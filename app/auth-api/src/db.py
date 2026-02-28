"""
PostgreSQL persistence for auth-api.

Defines SQLAlchemy models and helpers that are used by the auth repository:
- UserModel: core user identity
- FederatedModel: OIDC / federated mapping

This module is intentionally small; higher-level logic lives in
src.repositories.postgres_auth_repo.
"""

from contextlib import contextmanager
from typing import Generator, Optional
from datetime import datetime
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(nullable=False, default="")
    password: Mapped[str] = mapped_column(nullable=False, default="")

class FederatedModel(Base):
    __tablename__ = "federated"

    provider: Mapped[str] = mapped_column(primary_key=True)
    subject_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(nullable=False)

class RefreshTokenModel(Base):
    """Stored refresh tokens: one row per user (create or update on login)."""
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked: Mapped[bool] = mapped_column(nullable=False, default=False)

_engine = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def init_db() -> bool:
    """Create engine and tables. Returns True if DB is available."""
    global _engine, _SessionLocal
    url = (settings.AUTH_DB_URL or "").strip()
    if not url:
        logger.info("AUTH_DB_URL not set; auth-api will use in-memory user store")
        return False
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Auth DB connected; users and federated tables ready")
        return True
    except Exception as e:  # pragma: no cover - exercised in runtime
        logger.warning("Auth DB init failed: %s; using in-memory user store", e)
        _engine = None
        _SessionLocal = None
        return False


def is_db_available() -> bool:
    return _SessionLocal is not None


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError("DB not initialized")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - standard pattern
        session.rollback()
        raise
    finally:
        session.close()

