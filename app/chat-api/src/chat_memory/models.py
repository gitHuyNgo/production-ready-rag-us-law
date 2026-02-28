from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ChatMessageRecord(BaseModel):
    """Single message stored in chat memory."""

    session_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


