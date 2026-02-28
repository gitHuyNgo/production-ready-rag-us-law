# Chat Memory Architecture

## 1. Overview

LLMs are stateless. To support multi-turn conversations and RAG context, chat history must be stored externally. This project uses a **pluggable store** with a Cassandra implementation for production and an in-memory implementation for dev and tests.

## 2. Components

- **Client / Frontend**: Sends messages and (optionally) a session id; receives streamed or one-shot responses.
- **Chat API**: Orchestrates RAG, LLM, and chat memory. Reads recent messages from the store for context; appends user and assistant messages after each exchange.
- **ChatMemoryStore (interface)**: `list_sessions`, `get_recent_messages`, `append_messages`. Implementations in `app/chat-api/src/chat_memory/store.py`.
- **Cassandra (production)**: Durable, scalable store for message history. Keyspace `chat_memory`, table `messages` with `(session_id, timestamp)` as primary key and clustering by timestamp.
- **InMemoryChatMemoryStore (fallback)**: In-process dict keyed by session_id. Used when Cassandra is not configured or connection fails (e.g. `docker-compose.light.yml`, tests).

## 3. Data Model (Cassandra)

- **Partition key**: `session_id` — all messages in a conversation share the same partition for efficient reads.
- **Clustering**: `timestamp` — messages ordered chronologically within a session.
- **Columns**: `role`, `content` (and any additional metadata the app stores).
- **Schema**: Created on first use by `CassandraChatMemoryStore._ensure_schema()` (keyspace + table with replication factor 1 by default).

## 4. Flow

1. User sends a message (POST `/chat/` or WebSocket) with optional `X-Session-Id` (or query param).
2. Chat API loads recent messages for that session from the store (e.g. last N for context).
3. RAG pipeline runs (retrieval, rerank, LLM) using query and optional conversation context.
4. Response is streamed or returned; then user message and assistant message are appended to the store for that session.
5. Sessions can be listed via GET `/chat/sessions`; messages for a session via GET `/chat/sessions/{id}/messages`.

## 5. Why Cassandra (When Used)

- **Write scalability**: LSM-style design suits high write throughput for message append.
- **Availability**: No single master; replicas serve reads.
- **Partitioning**: By `session_id` keeps a conversation’s messages co-located for low-latency reads.
- **TTL**: Optional row-level TTL can be added for automatic expiry of old sessions.

When Cassandra is not run (e.g. light Compose), the in-memory store is used so the app still runs without external dependencies.
