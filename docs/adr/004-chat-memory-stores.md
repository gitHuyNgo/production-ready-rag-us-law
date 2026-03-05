# ADR 004: Chat Memory Stores — Cassandra with In-Memory Fallback

## Status

Accepted.

## Context

Chat API needs to persist conversation history per session. The LLM is stateless — each call needs the previous messages injected as context for multi-turn conversations to work:

```
Without memory:
  User: "What is the penalty for tax fraud?"
  Bot:  "Under 26 U.S.C. § 7201, up to 5 years..."
  User: "What about for corporations?"
  Bot:  "I don't have enough context."        ← doesn't know what "what about" refers to

With memory:
  User: "What is the penalty for tax fraud?"
  Bot:  "Under 26 U.S.C. § 7201, up to 5 years..."
  User: "What about for corporations?"
  Bot:  "For corporations, the fine is up to $500,000..."  ← loads previous messages as context
```

The store needs to handle:
- **Writes:** 2 messages per exchange (user + assistant), potentially 100s of exchanges per session
- **Reads:** Last 20 messages for one session (loaded on every request with a session ID)
- **Sessions:** Thousands of concurrent sessions across multiple chat-api pods

Production should be durable and shared across pods. Local dev and tests should work without external infrastructure.

## Decision

### Interface

```python
class ChatMemoryStore:
    def list_sessions(self, limit: int = 50) -> List[str]: ...
    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[ChatMessageRecord]: ...
    def append_messages(self, messages: List[ChatMessageRecord]) -> None: ...
```

All implementations in `app/chat-api/src/chat_memory/store.py`.

### Production: CassandraChatMemoryStore

```cql
CREATE KEYSPACE IF NOT EXISTS chat_memory
WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '1' };

CREATE TABLE IF NOT EXISTS chat_memory.messages (
    session_id text,
    timestamp  timestamp,
    role       text,
    content    text,
    PRIMARY KEY (session_id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp ASC);

CREATE TABLE IF NOT EXISTS chat_memory.sessions (
    session_id text PRIMARY KEY,
    updated_at timestamp
);
```

**Partition model:**

**Partition: session_id = "abc123"**

| timestamp | role | content |
| --- | --- | --- |
| 2025-03-01 12:00 | user | What is habeas corpus? |
| 2025-03-01 12:01 | assistant | Habeas corpus is a... |
| 2025-03-01 12:02 | user | When was it established? |
| 2025-03-01 12:03 | assistant | The concept dates back... |

Reading last 20 messages = single-partition scan = O(1) seek + O(20) read. Appending a message = single-partition INSERT = O(1) (LSM append).

### Fallback: InMemoryChatMemoryStore

```python
class InMemoryChatMemoryStore(ChatMemoryStore):
    def __init__(self):
        self._data: Dict[str, List[ChatMessageRecord]] = defaultdict(list)
```

### Selection at Startup

```python
try:
    memory_store = CassandraChatMemoryStore()
except Exception:
    memory_store = InMemoryChatMemoryStore()
```

No explicit feature flag. The behavior is environment-driven:
- If `cassandra-driver` is installed and Cassandra is reachable → Cassandra
- Otherwise → in-memory

## Alternatives Considered

### 1. PostgreSQL (auth-db)

**Approach:** Store messages in a `chat_messages` table in the existing auth PostgreSQL database.

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL
);
CREATE INDEX idx_session_id ON chat_messages (session_id, timestamp);
```

**Pros:**
- No new infrastructure — reuses the existing PostgreSQL
- ACID transactions
- Familiar tooling (SQLAlchemy, psql)

**Cons:**
- Couples auth and chat data in the same database
- PostgreSQL is not optimized for append-heavy workloads (B-tree inserts = random I/O)
- Auth-db downtime would affect both authentication AND chat history
- The connection pool is shared — heavy chat traffic could starve auth queries

**Why rejected:** Violates the service boundary (auth-api owns auth-db) and risks cascading failures.

### 2. MongoDB (user-db)

**Approach:** Store messages as documents in a `chat_sessions` collection.

```json
{
  "session_id": "abc123",
  "messages": [
    { "timestamp": "2025-03-01T12:00:00Z", "role": "user", "content": "..." },
    { "timestamp": "2025-03-01T12:01:00Z", "role": "assistant", "content": "..." }
  ]
}
```

**Pros:**
- Flexible schema
- Good read performance for loading a full session
- Reuses existing MongoDB

**Cons:**
- Appending to an array in a document requires `$push` — document grows and eventually needs migration
- MongoDB has a 16 MB document size limit — long sessions could hit this
- Couples user-api data with chat data

**Why rejected:** The growing-document pattern is problematic for chat history. Cassandra's row-per-message model is more natural.

### 3. Redis Streams

**Approach:** Use Redis Streams (`XADD`, `XRANGE`) to store messages.

```
XADD chat:abc123 * role user content "What is habeas corpus?"
XRANGE chat:abc123 - + COUNT 20
```

**Pros:**
- Extremely fast for append and recent reads
- Redis is already in the stack
- Built-in ordering by stream ID

**Cons:**
- Redis data is RAM-bound — storing months of chat history in memory is expensive
- Not designed for long-term persistence (RDB/AOF are for crash recovery, not archival)
- Would compete for memory with the semantic cache on the same Redis instance

**Why rejected:** Chat history can grow indefinitely. Storing it in RAM-based Redis is not cost-effective. Cassandra stores data on disk (EBS) which is 10x cheaper per GB.

### 4. DynamoDB

**Approach:** AWS-managed NoSQL with the same partition model as Cassandra.

```
Table: chat_messages
  Partition key: session_id
  Sort key: timestamp
```

**Pros:**
- Fully managed — no Cassandra operations
- Same partition-based access pattern
- On-demand pricing (pay per read/write)

**Cons:**
- AWS vendor lock-in
- Requires IAM roles for pod access (IRSA)
- More expensive than self-hosted Cassandra for write-heavy workloads
- Cannot run locally for development without LocalStack

**Why not chosen:** A valid option for production, but Cassandra was chosen to avoid vendor lock-in and allow local development with Docker Compose. DynamoDB could be adopted later as the production backend with minimal code changes (same interface).

### 5. SQLite / File-based

**Approach:** Each chat-api pod writes to a local SQLite file.

**Pros:** Zero infrastructure. Works everywhere.

**Cons:** Not shared across pods. Data lost on pod replacement. Cannot scale horizontally. Kubernetes pods have ephemeral filesystems by default.

**Why rejected:** Incompatible with Kubernetes multi-replica deployment.

## Consequences

### Positive

- **Single code path:** Same `ChatMemoryStore` interface for both stores. Router code doesn't change based on which store is active.
- **Graceful degradation:** If Cassandra is unavailable, the app still runs with in-memory store. Users can chat, but history is not persisted across restarts.
- **Right tool for the job:** Cassandra's LSM-tree append model is ideal for append-heavy chat history.
- **No infrastructure required for dev:** `docker-compose.light.yml` omits Cassandra, and the app works with in-memory.

### Negative

- **In-memory state is lost on restart.** Acceptable for dev/test, not for production.
- **In-memory is not shared across instances.** In Kubernetes with 2 chat-api pods, a user might get a different pod for each request and see inconsistent history. Mitigated by: always use Cassandra in production.
- **Cassandra operational complexity.** Compaction, tombstones, repair, and backup are non-trivial to manage. Consider a managed Cassandra service (Amazon Keyspaces, DataStax Astra) for production.
- **Schema and keyspace created on first use.** Replication factor defaults to 1. Production should set RF=3 with NetworkTopologyStrategy.

## Related

- [Chat Memory Architecture](../services/chat_memory_architecture.md) — full data flow and implementation details
- [Cassandra Chat Memory](../db/cassandra-chat-memory.md) — schema, queries, and storage details
