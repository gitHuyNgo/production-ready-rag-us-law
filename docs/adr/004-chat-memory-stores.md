# ADR 004: Chat Memory Stores — Cassandra with In-Memory Fallback

## Status

Accepted.

## Context

Chat API needs to persist conversation history per session for context in RAG and LLM calls. Production should use a scalable, durable store; local dev and tests should work without external infra.

## Decision

- **Interface**: `ChatMemoryStore` with `list_sessions`, `get_recent_messages`, `append_messages`. Implementations live in `app/chat-api/src/chat_memory/store.py`.
- **Production**: `CassandraChatMemoryStore` — connects to Cassandra (e.g. `cassandra:9042`), creates keyspace `chat_memory` and table `messages` with `(session_id, timestamp)` as primary key and clustering by timestamp. Used when `cassandra-driver` is available and connection succeeds.
- **Fallback**: `InMemoryChatMemoryStore` — in-process dict keyed by `session_id`. Used when Cassandra is not configured or connection fails (e.g. dev, tests, light Docker Compose without Cassandra).
- **Lifespan**: Chat API tries Cassandra first; on any exception it falls back to in-memory. No explicit feature flag; behavior is environment-driven.

## Consequences

- Single code path: same API for both stores. Production gets durability and scalability; dev/test avoid mandatory Cassandra.
- In-memory state is lost on restart and is not shared across instances; acceptable for non-production.
- Schema and keyspace are created on first use; replication factor and contact points are configurable via `CassandraChatMemoryStore` constructor (default keyspace `chat_memory`).
