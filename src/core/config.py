"""
Application configuration loaded from environment and .env files.
"""
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Environment file resolution
# ---------------------------------------------------------------------------
ENV_DEVELOPMENT = "development"
ENV_PRODUCTION = "production"
ENV_FILE_DEVELOPMENT = ".env.development"
ENV_FILE_PRODUCTION = ".env.production"
ENV_FILE_DEFAULT = ".env"


def get_env_file() -> str:
    """Resolve .env file path based on ENVIRONMENT variable."""
    env = os.getenv("ENVIRONMENT", ENV_DEVELOPMENT)
    env_files = {
        ENV_PRODUCTION: ENV_FILE_PRODUCTION,
        ENV_DEVELOPMENT: ENV_FILE_DEVELOPMENT,
    }
    target = env_files.get(env, ENV_FILE_DEFAULT)
    full_path = PROJECT_ROOT / target
    return str(full_path) if full_path.exists() else ENV_FILE_DEFAULT


class Settings(BaseSettings):
    """Application settings with validation and env loading."""
    APP_TITLE: str = "US Law RAG Controller"
    DEFAULT_HOST: str = "0.0.0.0"
    DEFAULT_PORT: int = 8000
    RERANKER_BM25_TOP_K: int = 10
    RERANKER_COHERE_TOP_K: int = 3
    
    OPENAI_API_KEY: str = Field(..., description="Key for OpenAI Embeddings and LLM")
    COHERE_API_KEY: str = Field(..., description="Key for Cohere Reranker")

    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_CLASS_NAME: str = Field(default="document_chunk_embedding")

    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model (3072 dims for 3-large, 1536 for 3-small/ada-002). Must match CACHE_EMBED_DIM.",
    )

    # Semantic cache (Redis Stack with RediSearch required for vector similarity)
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis URL for semantic cache (e.g. redis://localhost:6379). Empty = cache disabled.")
    CACHE_TTL_SECONDS: int = Field(default=86400, description="TTL for cached LLM responses (default 24h)")
    CACHE_SIMILARITY_THRESHOLD: float = Field(default=0.95, ge=0.0, le=1.0, description="Min cosine similarity to return cached response")
    CACHE_EMBED_DIM: int = Field(
        default=3072,
        description="Embedding dimension (must match embed model: 3072 for text-embedding-3-large, 1536 for 3-small/ada-002).",
    )

    ENVIRONMENT: str = Field(default=ENV_DEVELOPMENT)
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
