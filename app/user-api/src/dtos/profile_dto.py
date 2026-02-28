"""User profile DTOs for the user-api."""

from typing import Optional

from pydantic import BaseModel


class UserProfileDto(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

