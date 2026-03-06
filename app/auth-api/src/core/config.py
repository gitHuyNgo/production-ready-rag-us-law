"""
Auth-api configuration.
Load from .env in this service dir (app/auth-api/.env).
"""
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    return os.getenv("APP_ENV_FILE", ".env")


def _resolve_pem(path: str, content: str) -> str:
    if content:
        return content.replace("\\n", "\n")
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


class Settings(BaseSettings):
    AUTH_DB_URL: str = (
        "postgresql+psycopg2://auth_user:auth_pass@auth-db:5432/auth_db"
    )
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str = ""
    JWT_PRIVATE_KEY: str = ""

    JWT_PUBLIC_KEY_PATH: str = ""
    JWT_PUBLIC_KEY: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""

    SESSION_SECRET_KEY: str = "change-me-session-secret"
    FRONTEND_URL: str = "http://localhost:3000"

    KAFKA_BOOTSTRAP_SERVERS: str = ""
    KAFKA_USER_CREATED_TOPIC: str = "user.created"

    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _load_jwt_keys(self) -> "Settings":
        """Resolve JWT private and public keys once at startup from files or inline strings."""
        self.JWT_PRIVATE_KEY = _resolve_pem(self.JWT_PRIVATE_KEY_PATH, self.JWT_PRIVATE_KEY)
        self.JWT_PUBLIC_KEY = _resolve_pem(self.JWT_PUBLIC_KEY_PATH, self.JWT_PUBLIC_KEY)
        return self


settings = Settings()


