"""
FastAPI application entrypoint for US Law RAG Controller.
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.api.routers import chat_router, helper_router
from src.api.services.reranker_client import BM25Reranker, CohereReranker
from src.core.config import settings
from src.core.db_client import WeaviateClient
from src.core.llm_client import OpenAILLM

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: init resources on startup, cleanup on shutdown."""
    db = WeaviateClient()
    db.connect()

    llm = OpenAILLM()

    bm25_reranker = BM25Reranker(top_k=settings.RERANKER_BM25_TOP_K)
    cohere_reranker = CohereReranker(top_k=settings.RERANKER_COHERE_TOP_K)

    app.state.db = db
    app.state.llm = llm
    app.state.first_reranker = bm25_reranker
    app.state.second_reranker = cohere_reranker

    yield

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
