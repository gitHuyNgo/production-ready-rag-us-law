import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def get_env_file() -> str:
    env = os.getenv("ENVIRONMENT", "development")
    env_files = {
        "production": ".env.production",
        "development": ".env.development",
    }
    target = env_files.get(env, ".env")
    return str(PROJECT_ROOT / target) if os.path.exists(PROJECT_ROOT / target) else ".env"

class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(..., description="Key for OpenAI Embeddings and LLM")
    COHERE_API_KEY: str = Field(..., description="Key for Cohere Reranker")
    
    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_CLASS_NAME: str = Field(default="document_chunk_embedding")
    
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()