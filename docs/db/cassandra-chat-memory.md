# Cassandra Chat Memory

**Owner**: chat-api  
**Purpose**: Persist chat message history per session for RAG context and conversational continuity.

## Usage

- **Interface**: `ChatMemoryStore` with `list_sessions`, `get_recent_messages`, `append_messages`. Implementations in `app/chat-api/src/chat_memory/store.py`.
- **CassandraChatMemoryStore**: Connects to Cassandra (e.g. `cassandra:9042`), creates keyspace `chat_memory` and table `messages` if not present. Primary key `(session_id, timestamp)` with clustering by timestamp so messages in a session are ordered.
- **Fallback**: If Cassandra is unavailable (e.g. connection error or driver not installed), chat-api uses `InMemoryChatMemoryStore` so that dev and tests work without Cassandra. In-memory state is lost on restart and is not shared across instances.

## Schema (Cassandra)

```cql
CREATE KEYSPACE IF NOT EXISTS chat_memory
WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '1' };

CREATE TABLE IF NOT EXISTS chat_memory.messages (
    session_id text,
    timestamp timestamp,
    role text,
    content text,
    PRIMARY KEY (session_id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp ASC);
```

## Deployment

- Full Docker Compose includes a Cassandra service; `docker-compose.light.yml` omits it, so chat-api falls back to in-memory store in the light setup.
