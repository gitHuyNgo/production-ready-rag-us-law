"""
Ingestion worker service configuration (env + optional .env via APP_ENV_FILE).
"""
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    return os.getenv("APP_ENV_FILE", ".env")


class IngestionSettings(BaseSettings):
    """Settings for ingestion-worker (OpenAI, Weaviate, Redis)."""

    OPENAI_API_KEY: str = Field(default="", description="Key for OpenAI Embeddings")
    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_CLASS_NAME: str = Field(default="document_chunk_embedding")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-large")

    REDIS_URL: str = Field(default="redis://localhost:6379")
    CACHE_TTL_SECONDS: int = Field(default=86400)
    CACHE_SIMILARITY_THRESHOLD: float = Field(default=0.95, ge=0.0, le=1.0)
    CACHE_EMBED_DIM: int = Field(default=3072)

    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = IngestionSettings()
