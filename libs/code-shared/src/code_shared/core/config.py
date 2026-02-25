"""
Application configuration loaded from environment and .env file.
Use APP_ENV_FILE to point to the shared app/.env (e.g. ../.env when running from app/chat-api).
"""
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """Path to .env file. Set APP_ENV_FILE to app/.env for local dev (e.g. ../.env from app/chat-api)."""
    return os.getenv("APP_ENV_FILE", ".env")


class Settings(BaseSettings):
    """Shared settings for chat-api and ingestion-worker (env + optional .env file at APP_ENV_FILE)."""

    APP_TITLE: str = "US Law RAG Controller"
    DEFAULT_HOST: str = "127.0.0.1"
    DEFAULT_PORT: int = 8000
    RERANKER_BM25_TOP_K: int = 10
    RERANKER_COHERE_TOP_K: int = 3

    OPENAI_API_KEY: str = Field(..., description="Key for OpenAI Embeddings and LLM")
    COHERE_API_KEY: str = Field(..., description="Key for Cohere Reranker")

    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_CLASS_NAME: str = Field(default="document_chunk_embedding")

    COHERE_RERANKER_MODEL: str = Field(default="rerank-english-v3.0")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model. Must match CACHE_EMBED_DIM.",
    )
    OPENAI_LLM_MODEL: str = Field(default="gpt-5.1")

    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis URL for semantic cache. Empty = cache disabled.",
    )
    CACHE_TTL_SECONDS: int = Field(default=86400)
    CACHE_SIMILARITY_THRESHOLD: float = Field(default=0.95, ge=0.0, le=1.0)
    CACHE_EMBED_DIM: int = Field(default=3072, description="Embedding dimension.")

    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
