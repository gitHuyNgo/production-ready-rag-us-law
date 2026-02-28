"""
Chat-api configuration (env + optional .env file).

This is service-owned config (do not import shared config from libs at runtime).
Set APP_ENV_FILE to point to a shared env file if desired.
"""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    return os.getenv("APP_ENV_FILE", ".env")


class Settings(BaseSettings):
    APP_TITLE: str = "US Law RAG Controller"
    DEFAULT_HOST: str = "127.0.0.1"
    DEFAULT_PORT: int = 8000

    RERANKER_BM25_TOP_K: int = 10
    RERANKER_COHERE_TOP_K: int = 3

    # Keys are optional for unit tests; runtime will fail fast in lifespan if missing.
    OPENAI_API_KEY: str = Field(default="", description="Key for OpenAI Embeddings and LLM")
    COHERE_API_KEY: str = Field(default="", description="Key for Cohere Reranker (optional)")

    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_CLASS_NAME: str = Field(default="document_chunk_embedding")

    COHERE_RERANKER_MODEL: str = Field(default="rerank-english-v3.0")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-large")
    OPENAI_LLM_MODEL: str = Field(default="gpt-5.1")

    REDIS_URL: str = Field(default="redis://localhost:6379")
    CACHE_TTL_SECONDS: int = Field(default=86400)
    CACHE_SIMILARITY_THRESHOLD: float = Field(default=0.95, ge=0.0, le=1.0)
    CACHE_EMBED_DIM: int = Field(default=3072, description="Embedding dimension.")

    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

