"""
User-api configuration.
Load from .env in this service dir (app/user-api/.env).
"""
import os

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
    USER_DB_URL: str = "mongodb://user-db:27017/user_db"
    JWT_ALGORITHM: str = "RS256"
    JWT_PUBLIC_KEY: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""

    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def get_jwt_public_key() -> str:
    return _load_pem(settings.JWT_PUBLIC_KEY, settings.JWT_PUBLIC_KEY_PATH)

