"""
API Gateway configuration.
Load from .env in this service dir (app/api-gateway/.env).
"""
import os
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    return os.getenv("APP_ENV_FILE", ".env")


class Settings(BaseSettings):
    # Upstream services (URLs when running in Docker; use localhost when running gateway locally)
    AUTH_API_URL: str = "http://auth-api:8001"
    USER_API_URL: str = "http://user-api:8002"
    CHAT_API_URL: str = "http://chat-api:8000"

    # JWT verification (RS256: public key must match auth-api's key pair)
    JWT_ALGORITHM: str = "RS256"
    JWT_PUBLIC_KEY: str = ""
    JWT_PUBLIC_KEY_PATH: str = "public.pem"

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

    @model_validator(mode="after")
    def _load_public_key(self) -> "Settings":
        """Resolve JWT_PUBLIC_KEY once at startup from file or inline string."""
        if not self.JWT_PUBLIC_KEY and self.JWT_PUBLIC_KEY_PATH:
            if os.path.isfile(self.JWT_PUBLIC_KEY_PATH):
                with open(self.JWT_PUBLIC_KEY_PATH, "r", encoding="utf-8") as f:
                    self.JWT_PUBLIC_KEY = f.read()
        elif self.JWT_PUBLIC_KEY:
            self.JWT_PUBLIC_KEY = self.JWT_PUBLIC_KEY.replace("\\n", "\n")
        return self


settings = Settings()


def get_jwt_public_key() -> str:
    return settings.JWT_PUBLIC_KEY
