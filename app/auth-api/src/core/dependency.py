from src.repositories.base_auth_repo import BaseAuthRepository
from src.repositories.postgres_auth_repo import PostgreAuthRepository
from src.service.auth_service import AuthService

def get_auth_repo() -> BaseAuthRepository:
    # For now always Postgres-backed repo with in‑memory fallback.
    # FastAPI will create a new instance per request by default.
    return PostgreAuthRepository()

def get_auth_service() -> AuthService:
    repo = PostgreAuthRepository()
    return AuthService(repo=repo)
    