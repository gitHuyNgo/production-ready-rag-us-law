import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.api.routers import chat_router, helper_router
from src.core.config import settings
from src.core.db_client import WeaviateClient
from src.core.llm_client import OpenAILLM
from src.api.services.reranker_client import BM25Reranker, CohereReranker

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing RAG Controller...")
    
    db = WeaviateClient()
    db.connect()
    
    llm = OpenAILLM()
    
    bm25 = BM25Reranker(top_k=10)
    cohere = CohereReranker(top_k=3)
    
    app.state.db = db
    app.state.llm = llm
    app.state.first_reranker = bm25
    app.state.second_reranker = cohere
    
    yield
    
    print("🛑 Closing connections...")
    db.close()

app = FastAPI(
    title="US Law RAG Controller",
    lifespan=lifespan
)

app.include_router(chat_router.router)
app.include_router(helper_router.router)

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)