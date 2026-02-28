from typing import Optional, Tuple, Dict
from datetime import datetime
from sqlalchemy import select, func

from src.models.auth import User
from src.repositories.base_auth_repo import BaseAuthRepository

try:
    from src.db import (
        UserModel,
        FederatedModel,
        RefreshTokenModel,
        get_db_session,
        is_db_available,
    )
except ImportError:  # e.g. tests without DB
    UserModel = FederatedModel = RefreshTokenModel = None  # type: ignore

    def is_db_available() -> bool:  # type: ignore[func-returns-value]
        return False

    def get_db_session():  # type: ignore[func-returns-value]
        raise RuntimeError("DB not available")


class PostgreAuthRepository(BaseAuthRepository):
    """
    Repository backed by PostgreSQL when available, otherwise an in‑memory store.
    """

    def __init__(self) -> None:
        # In‑memory fallback (used if init_db() failed or AUTH_DB_URL unset)
        self._memory_users: Dict[str, User] = {}
        self._memory_federated: Dict[Tuple[str, str], str] = {}

    def _use_db(self) -> bool:
        try:
            return bool(is_db_available())
        except Exception:
            return False

    # ---------- helpers ----------

    @staticmethod
    def _row_to_user(row) -> User:
        return User(
            username=row.username,
            email=row.email or "",
            password=row.password or "",
        )

    # ---------- user CRUD ----------

    def get_by_username(self, username: str) -> Optional[User]:
        if self._use_db() and UserModel is not None:
            with get_db_session() as session:
                row = session.get(UserModel, username)
                if row:
                    return self._row_to_user(row)
            return None
        return self._memory_users.get(username)

    def get_by_email(self, email: str) -> Optional[User]:
        key = email.strip().lower()
        if not key:
            return None

        if self._use_db() and UserModel is not None:
            with get_db_session() as session:
                row = (
                    session.execute(
                        select(UserModel).where(func.lower(UserModel.email) == key)
                    )
                    .scalars()
                    .first()
                )
                if row:
                    return self._row_to_user(row)
            return None

        for u in self._memory_users.values():
            if u.email and u.email.strip().lower() == key:
                return u
        return None

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None

    def create_user(self, username: str, email: str, password_hash: str) -> User:
        if self._use_db() and UserModel is not None:
            with get_db_session() as session:
                existing = session.get(UserModel, username)
                if existing:
                    raise ValueError("Username already registered")
                row = UserModel(username=username, email=email or "", password=password_hash)
                session.add(row)
            return User(username=username, email=email or "", password=password_hash)

        if username in self._memory_users:
            raise ValueError("Username already registered")
        user = User(username=username, email=email or "", password=password_hash)
        self._memory_users[username] = user
        return user

    # ---------- federated ----------

    def get_by_federated(self, provider: str, subject_id: str) -> Optional[User]:
        key = (provider, subject_id)

        if self._use_db() and FederatedModel is not None:
            with get_db_session() as session:
                row = (
                    session.execute(
                        select(FederatedModel).where(
                            FederatedModel.provider == provider,
                            FederatedModel.subject_id == subject_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if row:
                    return self.get_by_username(row.user_id)
            return None

        username = self._memory_federated.get(key)
        return self._memory_users.get(username) if username else None

    def create_federated_user(
        self,
        provider: str,
        subject_id: str,
        username: str,
        email: str,
    ) -> User:
        if self._use_db() and UserModel is not None and FederatedModel is not None:
            with get_db_session() as session:
                if session.get(UserModel, username):
                    raise ValueError("Username already registered")
                session.add(UserModel(username=username, email=email or "", password=""))
                session.add(
                    FederatedModel(
                        provider=provider,
                        subject_id=subject_id,
                        user_id=username,
                    )
                )
            return User(username=username, email=email or "", password="")

        if username in self._memory_users:
            raise ValueError("Username already registered")
        user = User(username=username, email=email or "", password="")
        self._memory_users[username] = user
        self._memory_federated[(provider, subject_id)] = username
        return user

    # ---------- refresh token (create or update on login) ----------

    def save_refresh_token(
        self,
        user_id: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> None:
        if self._use_db() and RefreshTokenModel is not None:
            with get_db_session() as session:
                row = session.get(RefreshTokenModel, user_id)
                if row:
                    row.token = refresh_token
                    row.expires_at = expires_at
                    row.revoked = False
                else:
                    session.add(
                        RefreshTokenModel(
                            user_id=user_id,
                            token=refresh_token,
                            expires_at=expires_at,
                            revoked=False,
                        )
                    )
        # In-memory: no-op (optional: keep a dict if you need to validate refresh tokens later)