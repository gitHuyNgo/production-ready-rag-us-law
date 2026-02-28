"""
API Gateway configuration.
Load from .env in this service dir (app/api-gateway/.env).
"""
import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    return os.getenv("APP_ENV_FILE", ".env")


def _load_pem(content: str, path: str) -> str:
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    if content:
        return content.replace("\\n", "\n")
    return ""


class Settings(BaseSettings):
    # Upstream services (URLs when running in Docker; use localhost when running gateway locally)
    AUTH_API_URL: str = "http://auth-api:8001"
    USER_API_URL: str = "http://user-api:8002"
    CHAT_API_URL: str = "http://chat-api:8000"

    # JWT verification (RS256: public key must match auth-api's key pair)
    JWT_ALGORITHM: str = "RS256"
    JWT_PUBLIC_KEY: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Rate limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_STRICT: str = "20/minute"  # auth, login

    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def get_jwt_public_key() -> str:
    return _load_pem(settings.JWT_PUBLIC_KEY, settings.JWT_PUBLIC_KEY_PATH)
