# Chat API

The Chat API provides RAG-based Q&A and conversational chat. It is exposed via the gateway at `/chat/*`. It uses Weaviate for retrieval, BM25 + Cohere for reranking, OpenAI for the LLM, Redis for semantic cache, and Cassandra (or in-memory) for chat history.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/chat/sessions` | Optional | List chat session IDs (from chat memory store). |
| GET | `/chat/sessions/{session_id}/messages` | Optional | Get recent messages for a session. |
| POST | `/chat/` | Optional | One-shot RAG query. Body: `{ "content": "question" }`. Optional header `X-Session-Id` for chat memory. Returns full text response. |
| WebSocket | `/chat/` | Bearer (header) | Streaming chat. Client sends JSON messages; server streams tokens. Query params (e.g. `session_id`) forwarded by gateway. |

## RAG Pipeline

1. **Semantic cache** (optional): If Redis is configured and query embedding matches a cached query above similarity threshold, return cached response.
2. **Retrieval**: Query Weaviate (vector + metadata) for top-k chunks.
3. **Rerank**: First pass with BM25 reranker, then Cohere reranker to reduce to final top-k.
4. **Context**: Formatted context string built from chunks (source + text).
5. **LLM**: OpenAI (or configured LLM) generates answer from context + query. Supports streaming.

Chat memory is appended after each exchange (user message + assistant response) when `X-Session-Id` is provided and chat_memory store is available.

## Configuration

- Weaviate URL and class name, Redis URL, OpenAI API key, embedding model, reranker top-k values, and cache TTL/similarity/embed_dim are set via environment (e.g. `api/core/config.py`). Chat memory uses Cassandra if reachable; otherwise falls back to in-memory store.
