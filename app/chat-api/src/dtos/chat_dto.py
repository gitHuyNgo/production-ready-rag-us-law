"""
Data transfer objects for chat API.
"""
from enum import Enum
from typing import List

from pydantic import BaseModel


class Role(str, Enum):
    """Chat message role."""

    user = "user"
    agent = "agent"


class ChatMessageDto(BaseModel):
    """Single chat message."""

    role: Role
    content: str


class ChatDto(BaseModel):
    """Chat request with history and current message."""

    history: List[ChatMessageDto]
    role: Role
    content: str


ChatDto.model_rebuild()
