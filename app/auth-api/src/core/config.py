"""
Auth-api configuration.
Load from .env in this service dir (app/auth-api/.env).
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

def _env_file() -> str:
    return os.getenv("APP_ENV_FILE", ".env")

class Settings(BaseSettings):
    AUTH_DB_URL: str = (
        "postgresql+psycopg2://auth_user:auth_pass@auth-db:5432/auth_db"
    )
    JWT_ALGORITHM: str = "RS256"
    # RS256: private key for signing tokens (auth-api only)
    JWT_PRIVATE_KEY_PATH: str = ""
    # RS256: public key for verifying tokens (auth-api needs for /me; gateway/user-api use their own copy)
    JWT_PUBLIC_KEY_PATH: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    SESSION_SECRET_KEY: str = "change-me-session-secret"
    FRONTEND_URL: str = "http://localhost:3000"

    # Kafka (optional; if unset, UserCreated uses in-memory publisher)
    KAFKA_BOOTSTRAP_SERVERS: str = ""
    KAFKA_USER_CREATED_TOPIC: str = "user.created"

    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


