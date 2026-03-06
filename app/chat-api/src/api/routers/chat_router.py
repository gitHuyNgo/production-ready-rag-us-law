import asyncio
import json
from queue import Queue

from fastapi import APIRouter, Header, Request, WebSocket, WebSocketDisconnect

from src.api.services.rag_pipeline import answer, answer_stream
from src.dtos.chat_dto import ChatDto

router = APIRouter(prefix="/chat", tags=["chat"])


def _scoped_session_id(session_id: str | None, user_id: str | None) -> str:
    """Prefix session_id with user_id so sessions are isolated per user.

    Anonymous requests (no user_id) use a flat global namespace as before.
    Authenticated requests use '<user_id>:<session_id>' so two users with the
    same session label never share history.
    """
    base = session_id or "default"
    if user_id:
        return f"{user_id}:{base}"
    return base


@router.get("/sessions")
async def list_sessions(
    request: Request,
    limit: int = 50,
    x_user_id: str | None = Header(default=None),
):
    """List chat session ids (from Cassandra), scoped to the requesting user."""
    chat_memory = getattr(request.app.state, "chat_memory", None)
    if chat_memory is None:
        return {"session_ids": []}
    try:
        all_ids = chat_memory.list_sessions(limit=min(limit, 100))
        if x_user_id:
            prefix = f"{x_user_id}:"
            session_ids = [sid[len(prefix):] for sid in all_ids if sid.startswith(prefix)]
        else:
            session_ids = []
        return {"session_ids": session_ids}
    except Exception:
        return {"session_ids": []}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    request: Request,
    session_id: str,
    limit: int = 20,
    x_user_id: str | None = Header(default=None),
):
    """Get recent messages for a session (from Cassandra), scoped to the requesting user."""
    chat_memory = getattr(request.app.state, "chat_memory", None)
    if chat_memory is None:
        return {"messages": []}
    try:
        scoped_id = _scoped_session_id(session_id, x_user_id)
        records = chat_memory.get_context(scoped_id, limit=min(limit, 100))
        return {
            "messages": [
                {"role": r.role, "content": r.content, "timestamp": r.timestamp.isoformat()}
                for r in records
            ]
        }
    except Exception:
        return {"messages": []}


def _get_query_embedding_fn(embed_model):
    """Return a callable that embeds query text, or None if no embed model."""
    if embed_model is None:
        return None
    return lambda q: embed_model.get_text_embedding(q)


@router.post("/")
async def chat_post(
    request: Request,
    dto: ChatDto,
    x_session_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    """Handle chat via POST: same contract as WebSocket, single response."""
    db = request.app.state.db
    llm = request.app.state.llm
    first_reranker = request.app.state.first_reranker
    second_reranker = request.app.state.second_reranker
    semantic_cache = getattr(request.app.state, "semantic_cache", None)
    get_query_embedding = _get_query_embedding_fn(getattr(request.app.state, "embed_model", None))

    result = await asyncio.to_thread(
        answer,
        db=db,
        llm=llm,
        first_reranker=first_reranker,
        second_reranker=second_reranker,
        query=dto.content,
        semantic_cache=semantic_cache,
        get_query_embedding=get_query_embedding,
    )

    # Persist exchange to chat memory if available
    session_id = _scoped_session_id(x_session_id, x_user_id)
    chat_memory = getattr(request.app.state, "chat_memory", None)
    if chat_memory is not None:
        try:
            chat_memory.append_exchange(session_id, dto.content, result)
        except Exception:
            # chat memory failures should not break the main flow
            pass
    return {
        "history": [m.model_dump() for m in dto.history],
        "received_role": "assistant",
        "received_content": result,
        "history_length": len(dto.history),
    }


def _run_stream_into_queue(thread_queue: Queue, stream_args: dict) -> None:
    """Run sync answer_stream and put chunks + done into thread-safe queue."""
    try:
        chunks = []
        for chunk in answer_stream(**stream_args):
            chunks.append(chunk)
            thread_queue.put(("chunk", chunk))
        thread_queue.put(("done", "".join(chunks)))
    except Exception as e:  # pragma: no cover - defensive; tested via integration
        thread_queue.put(("error", str(e)))


@router.websocket("/")
async def chat_websocket(websocket: WebSocket):
    """Handle chat over WebSocket: stream RAG response tokens, then send done."""
    await websocket.accept()

    db = websocket.app.state.db
    llm = websocket.app.state.llm
    first_reranker = websocket.app.state.first_reranker
    second_reranker = websocket.app.state.second_reranker
    semantic_cache = getattr(websocket.app.state, "semantic_cache", None)
    get_query_embedding = _get_query_embedding_fn(getattr(websocket.app.state, "embed_model", None))

    raw_session_id = (
        websocket.headers.get("x-session-id")
        or websocket.query_params.get("session_id")
    )
    user_id = websocket.headers.get("x-user-id")
    session_id = _scoped_session_id(raw_session_id, user_id)
    chat_memory = getattr(websocket.app.state, "chat_memory", None)

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            dto = ChatDto.model_validate(payload)

            thread_queue = Queue()
            stream_args = {
                "db": db,
                "llm": llm,
                "first_reranker": first_reranker,
                "second_reranker": second_reranker,
                "query": dto.content,
                "semantic_cache": semantic_cache,
                "get_query_embedding": get_query_embedding,
            }
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None, _run_stream_into_queue, thread_queue, stream_args
            )

            def get_from_thread():
                return thread_queue.get()

            history_payload = [m.model_dump() for m in dto.history]
            history_len = len(dto.history)

            while True:
                msg = await asyncio.wait_for(
                    loop.run_in_executor(None, get_from_thread),
                    timeout=300.0,
                )
                kind, value = msg
                if kind == "chunk":
                    await websocket.send_text(
                        json.dumps({"t": "chunk", "content": value})
                    )
                elif kind == "done":
                    # Append full exchange into chat memory if available
                    if chat_memory is not None:
                        try:
                            chat_memory.append_exchange(session_id, dto.content, value)
                        except Exception:
                            pass
                    await websocket.send_text(
                        json.dumps({
                            "t": "done",
                            "received_content": value,
                            "history": history_payload,
                            "received_role": "assistant",
                            "history_length": history_len,
                        })
                    )
                    break
                else:  # pragma: no cover - error from pipeline/queue
                    await websocket.send_text(
                        json.dumps({"t": "error", "error": value})
                    )
                    break
    except WebSocketDisconnect:  # pragma: no cover - client disconnect
        pass
    except json.JSONDecodeError as e:  # pragma: no cover - invalid payload
        await websocket.send_text(
            json.dumps({"t": "error", "error": f"Invalid JSON: {e!s}"})
        )
    except Exception as e:  # pragma: no cover - validation or pipeline error
        await websocket.send_text(
            json.dumps({"t": "error", "error": str(e)})
        )
    finally:  # pragma: no cover - cleanup
        try:
            await websocket.close()
        except Exception:
            pass
