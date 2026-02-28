"""Auth domain models (aligned with authentication_architecture.md).

These are internal/domain models, separate from DTOs in src.dtos.auth.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    username: str
    email: str
    password: str = ""


class Federated(BaseModel):
    user_id: str
    provider: str  # e.g. 'google', 'github'
    subject_id: str  # unique ID from the external identity provider


class RefreshToken(BaseModel):
    token: str
    user_id: str  # PydanticObjectId in doc; str keeps DB agnostic
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
