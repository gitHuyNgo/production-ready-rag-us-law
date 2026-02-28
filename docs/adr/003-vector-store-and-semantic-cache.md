# ADR 003: Vector Store and Semantic Cache Ownership

## Status

Accepted.

## Context

Weaviate (vector store) and Redis (semantic cache for RAG) were initially in a shared library. This pulled heavy dependencies into every consumer and blurred ownership: chat-api reads and uses the cache; ingestion-worker writes to Weaviate and must invalidate the cache after re-ingestion.

## Decision

- **Chat API** owns:
  - **Weaviate**: Full client (connect, retrieve, embed) for RAG retrieval. Lives under `app/chat-api/src/vector_store/`.
  - **Redis semantic cache**: Full implementation (get/set, vector index, TTL). Lives under `app/chat-api/src/semantic_cache.py`.
- **Ingestion Worker** owns:
  - Its own **Weaviate** client (write + schema init only; no retrieve). Lives under `app/ingestion-worker/src/vector_store/`.
  - A **flush-only** semantic cache module that uses the same Redis key prefix/index as chat-api, so a run of the ingestion worker clears chat-api’s RAG cache after ingest.
- **Shared library** (`libs/code-shared`): No Weaviate or Redis. Only exceptions, LLM interfaces, and shared utilities. Each service has its own config and dependencies (e.g. `weaviate-client`, `redis` in respective `requirements.txt`).

## Consequences

- Chat-api and ingestion-worker can evolve their vector/cache logic independently. Clear ownership and fewer cross-service dependencies.
- Duplication of Weaviate client and schema code between chat-api and ingestion-worker; kept minimal (ingestion-worker does not implement retrieve).
- Semantic cache contract: same Redis URL, key prefix, and embed dimension so flush in ingestion-worker matches what chat-api uses.
