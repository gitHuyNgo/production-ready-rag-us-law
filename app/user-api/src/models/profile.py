"""User profile domain model."""

from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

