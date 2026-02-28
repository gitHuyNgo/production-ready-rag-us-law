"""Chat memory service helpers."""
from datetime import datetime
from typing import List

from .models import ChatMessageRecord
from .store import ChatMemoryStore


class ChatMemoryService:
    """High-level operations for chat memory."""

    def __init__(self, store: ChatMemoryStore) -> None:
        self._store = store

    def list_sessions(self, limit: int = 50) -> List[str]:
        return self._store.list_sessions(limit=limit)

    def get_context(self, session_id: str, limit: int = 20) -> List[ChatMessageRecord]:
        return self._store.get_recent_messages(session_id, limit=limit)

    def append_exchange(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        now = datetime.utcnow()
        records = [
            ChatMessageRecord(
                session_id=session_id,
                role="user",
                content=user_message,
                timestamp=now,
            ),
            ChatMessageRecord(
                session_id=session_id,
                role="assistant",
                content=assistant_message,
                timestamp=now,
            ),
        ]
        self._store.append_messages(records)

