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

    OPENAI_API_KEY: str = Field(..., description="Key for OpenAI Embeddings and LLM")
    COHERE_API_KEY: str = Field(..., description="Key for Cohere Reranker")

    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_CLASS_NAME: str = Field(default="document_chunk_embedding")

    ENVIRONMENT: str = Field(default=ENV_DEVELOPMENT)
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
