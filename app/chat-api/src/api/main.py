"""
FastAPI application entrypoint for US Law RAG Controller.
"""
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from src.api.routers import chat_router, helper_router
from src.api.services.reranker_client import BM25Reranker, CohereReranker
from src.chat_memory.service import ChatMemoryService
from src.chat_memory.store import CassandraChatMemoryStore, InMemoryChatMemoryStore
from code_shared.llm import OpenAILLM
from src.api.core.config import settings
from src.vector_store import WeaviateClient
from src.semantic_cache import SemanticCache

# Prompts live in chat-api (not code-shared)
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: init resources on startup, cleanup on shutdown."""
    # Tests can pre-populate `app.state` with fakes before startup.
    if getattr(app.state, "db", None) is not None and getattr(app.state, "llm", None) is not None:
        yield
        return

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required to run chat-api")

    db = WeaviateClient(
        weaviate_url=settings.WEAVIATE_URL,
        weaviate_class_name=settings.WEAVIATE_CLASS_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_embedding_model=settings.OPENAI_EMBEDDING_MODEL,
    )
    db.connect()

    llm = OpenAILLM(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_LLM_MODEL,
        prompt_dir=_PROMPTS_DIR,
    )

    bm25_reranker = BM25Reranker(top_k=settings.RERANKER_BM25_TOP_K)
    cohere_reranker = CohereReranker(top_k=settings.RERANKER_COHERE_TOP_K)
    semantic_cache = SemanticCache(
        redis_url=settings.REDIS_URL,
        ttl_seconds=settings.CACHE_TTL_SECONDS,
        similarity_threshold=settings.CACHE_SIMILARITY_THRESHOLD,
        embed_dim=settings.CACHE_EMBED_DIM,
    )

    # Chat memory: try Cassandra, fall back to in-memory store for dev/tests.
    try:
        memory_store = CassandraChatMemoryStore()
    except Exception:  # pragma: no cover - exercised via integration
        memory_store = InMemoryChatMemoryStore()
    chat_memory = ChatMemoryService(memory_store)

    app.state.db = db
    app.state.llm = llm
    app.state.first_reranker = bm25_reranker
    app.state.second_reranker = cohere_reranker
    app.state.semantic_cache = semantic_cache
    app.state.embed_model = getattr(db, "embed_model", None)
    app.state.chat_memory = chat_memory

    yield

    semantic_cache.close()
    # Close chat memory store if it has a close() method
    store = getattr(app.state, "chat_memory", None)
    close_fn = getattr(getattr(store, "_store", None), "close", None)
    if callable(close_fn):
        close_fn()
    if db.client:
        db.close()


app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

app.include_router(chat_router.router)
app.include_router(helper_router.router)

if __name__ == "__main__":  # pragma: no cover - manual server entrypoint
    uvicorn.run(
        "src.api.main:app",
        host=settings.DEFAULT_HOST,
        port=settings.DEFAULT_PORT,
        reload=True,
    )
