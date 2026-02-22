import asyncio
import json
from queue import Queue

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from src.api.services.rag_pipeline import answer, answer_stream
from src.dtos.chat_dto import ChatDto

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
async def chat_post(request: Request, dto: ChatDto):
    """Handle chat via POST: same contract as WebSocket, single response."""
    db = request.app.state.db
    llm = request.app.state.llm
    first_reranker = request.app.state.first_reranker
    second_reranker = request.app.state.second_reranker

    result = await asyncio.to_thread(
        answer,
        db=db,
        llm=llm,
        first_reranker=first_reranker,
        second_reranker=second_reranker,
        query=dto.content,
    )
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
    except Exception as e:
        thread_queue.put(("error", str(e)))


@router.websocket("/")
async def chat_websocket(websocket: WebSocket):
    """Handle chat over WebSocket: stream RAG response tokens, then send done."""
    await websocket.accept()

    db = websocket.app.state.db
    llm = websocket.app.state.llm
    first_reranker = websocket.app.state.first_reranker
    second_reranker = websocket.app.state.second_reranker

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
                else:
                    await websocket.send_text(
                        json.dumps({"t": "error", "error": value})
                    )
                    break
    except WebSocketDisconnect:
        pass
    except json.JSONDecodeError as e:
        await websocket.send_text(
            json.dumps({"t": "error", "error": f"Invalid JSON: {e!s}"})
        )
    except Exception as e:
        await websocket.send_text(
            json.dumps({"t": "error", "error": str(e)})
        )
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
