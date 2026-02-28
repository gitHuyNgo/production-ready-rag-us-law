from datetime import datetime, timedelta

from src.chat_memory.models import ChatMessageRecord
from src.chat_memory.service import ChatMemoryService
from src.chat_memory.store import InMemoryChatMemoryStore


def test_chat_memory_service_appends_and_reads_back_in_order():
    store = InMemoryChatMemoryStore()
    service = ChatMemoryService(store)

    session_id = "session-1"

    # Seed some existing messages with older timestamps
    earlier = datetime.now() - timedelta(minutes=10)
    store.append_messages(
        [
            ChatMessageRecord(
                session_id=session_id,
                role="user",
                content="old user",
                timestamp=earlier,
            ),
            ChatMessageRecord(
                session_id=session_id,
                role="assistant",
                content="old assistant",
                timestamp=earlier,
            ),
        ]
    )

    # Append a new exchange via the service
    service.append_exchange(session_id, "new user", "new assistant")

    messages = service.get_context(session_id, limit=10)
    assert len(messages) == 4
    # Messages should be in chronological order
    contents = [m.content for m in messages]
    assert contents == ["old user", "old assistant", "new user", "new assistant"]

