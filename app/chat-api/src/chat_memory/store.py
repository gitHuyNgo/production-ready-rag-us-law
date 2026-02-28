"""Chat memory store implementations."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from .models import ChatMessageRecord


class ChatMemoryStore:
    """Interface for chat memory stores."""

    def list_sessions(self, limit: int = 50) -> List[str]:
        """Return session ids, most recently updated first."""
        raise NotImplementedError

    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[ChatMessageRecord]:
        raise NotImplementedError

    def append_messages(self, messages: List[ChatMessageRecord]) -> None:
        raise NotImplementedError


class InMemoryChatMemoryStore(ChatMemoryStore):
    """Simple in-memory implementation for tests and local dev."""

    def __init__(self) -> None:
        self._data: Dict[str, List[ChatMessageRecord]] = defaultdict(list)

    def list_sessions(self, limit: int = 50) -> List[str]:
        # No ordering by updated_at; return keys
        return list(self._data.keys())[-limit:]

    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[ChatMessageRecord]:
        items = self._data.get(session_id, [])
        return sorted(items, key=lambda m: m.timestamp)[-limit:]

    def append_messages(self, messages: List[ChatMessageRecord]) -> None:
        for msg in messages:
            self._data[msg.session_id].append(msg)


try:
    from cassandra.cluster import Cluster  # type: ignore[import]
except ImportError:  # pragma: no cover - driver not installed in some environments
    Cluster = None  # type: ignore[assignment]


class CassandraChatMemoryStore(ChatMemoryStore):
    """Cassandra-backed chat memory store.

    This implementation expects a keyspace and table with a schema like:

        CREATE TABLE IF NOT EXISTS chat_memory.messages (
            session_id text,
            timestamp timestamp,
            role text,
            content text,
            PRIMARY KEY (session_id, timestamp)
        ) WITH CLUSTERING ORDER BY (timestamp ASC);
    """

    def __init__(self, contact_points: str = "cassandra:9042", keyspace: str = "chat_memory") -> None:
        if Cluster is None:
            raise RuntimeError("cassandra-driver not installed")
        hosts = [hp.strip() for hp in contact_points.split(",") if hp.strip()]
        self._cluster = Cluster(hosts)
        self._session = self._cluster.connect()
        self._ensure_schema(keyspace)
        self._session.set_keyspace(keyspace)

    def _ensure_schema(self, keyspace: str) -> None:
        self._session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{ 'class': 'SimpleStrategy', 'replication_factor': '1' }}
            """
        )
        self._session.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_memory.messages (
                session_id text,
                timestamp timestamp,
                role text,
                content text,
                PRIMARY KEY (session_id, timestamp)
            ) WITH CLUSTERING ORDER BY (timestamp ASC)
            """
        )
        self._session.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_memory.sessions (
                session_id text PRIMARY KEY,
                updated_at timestamp
            )
            """
        )

    def list_sessions(self, limit: int = 50) -> List[str]:
        rows = self._session.execute(
            "SELECT session_id FROM sessions ORDER BY updated_at DESC LIMIT %s",
            (limit,),
        )
        return [row.session_id for row in rows]

    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[ChatMessageRecord]:
        rows = self._session.execute(
            "SELECT session_id, timestamp, role, content FROM messages WHERE session_id=%s ORDER BY timestamp ASC LIMIT %s",
            (session_id, limit),
        )
        return [
            ChatMessageRecord(
                session_id=row.session_id,
                timestamp=row.timestamp,
                role=row.role,
                content=row.content,
            )
            for row in rows
        ]

    def append_messages(self, messages: List[ChatMessageRecord]) -> None:
        for msg in messages:
            self._session.execute(
                "INSERT INTO messages (session_id, timestamp, role, content) VALUES (%s, %s, %s, %s)",
                (msg.session_id, msg.timestamp, msg.role, msg.content),
            )
            self._session.execute(
                "INSERT INTO sessions (session_id, updated_at) VALUES (%s, %s)",
                (msg.session_id, msg.timestamp),
            )

    def close(self) -> None:
        self._cluster.shutdown()

