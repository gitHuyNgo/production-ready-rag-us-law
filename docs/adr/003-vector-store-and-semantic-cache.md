# ADR 003: Vector Store and Semantic Cache Ownership

## Status

Accepted.

## Context

Two services interact with Weaviate (vector store) and Redis (semantic cache):

- **chat-api** reads from Weaviate (RAG retrieval) and uses Redis for caching (get/set)
- **ingestion-worker** writes to Weaviate (batch load) and flushes Redis cache after ingestion

Initially, both Weaviate client and Redis semantic cache code lived in a shared library (`libs/code-shared`). This caused problems:

1. **Dependency bloat:** Every service that imported `code-shared` pulled in `weaviate-client` (150+ MB), `redis`, `numpy` — even services that don't use Weaviate or Redis (like auth-api)
2. **Unclear ownership:** Who owns the Weaviate schema? Who defines the Redis index? Changes to the cache could break both services simultaneously.
3. **Coupled evolution:** ingestion-worker only needs `batch_load()` and `initialize_schema()` but was importing a full client with `retrieve()`, `close()`, and cache `get()/set()` methods it never used.

## Decision

Each service owns its own Weaviate client and semantic cache module. The shared library contains only exceptions, LLM interfaces, and utilities — no Weaviate or Redis code.

```
┌─────────────────────────────────┐    ┌──────────────────────────────────┐
│         chat-api                │    │      ingestion-worker            │
│                                 │    │                                  │
│  src/vector_store/              │    │  src/vector_store/               │
│    weaviate_client.py           │    │    weaviate_client.py            │
│    ├── connect()                │    │    ├── connect()                 │
│    ├── retrieve() ✓             │    │    ├── retrieve() → raises       │
│    ├── batch_load() ✓           │    │    │   NotImplementedError       │
│    ├── initialize_schema() ✓    │    │    ├── batch_load() ✓            │
│    └── close() ✓                │    │    ├── initialize_schema() ✓     │
│                                 │    │    └── close() ✓                 │
│  src/semantic_cache.py          │    │                                  │
│    ├── get() ✓                  │    │  src/semantic_cache.py           │
│    ├── set() ✓                  │    │    ├── get() → NOT USED          │
│    ├── flush() ✓                │    │    ├── set() → NOT USED          │
│    └── close() ✓                │    │    ├── flush() ✓                 │
│                                 │    │    └── close() ✓                 │
└─────────────────────────────────┘    └──────────────────────────────────┘

┌──────────────────────────────────┐
│     libs/code-shared             │
│                                  │
│  core/exceptions.py              │  ← AppError, shared error types
│  llm/base.py                     │  ← BaseLLM interface
│  llm/openai_llm.py               │  ← OpenAILLM implementation
│                                  │
│  NO Weaviate code                │
│  NO Redis code                   │
│  NO numpy                        │
└──────────────────────────────────┘
```

### Contract Between Services

Both services must agree on these shared constants (enforced by convention, not by code):

| Constant | chat-api value | ingestion-worker value | Must match? |
| --- | --- | --- | --- |
| `WEAVIATE_CLASS_NAME` | `document_chunk_embedding` | `document_chunk_embedding` | **Yes** — same collection |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-large` | `text-embedding-3-large` | **Yes** — same vector dimensions |
| `CACHE_PREFIX` | `rag_cache:` | `rag_cache:` | **Yes** — flush must match cache keys |
| `INDEX_NAME` | `rag_cache_idx` | `rag_cache_idx` | **Yes** — flush drops the right index |
| `CACHE_EMBED_DIM` | `3072` | `3072` | **Yes** — must match embedding model |

If any of these diverge, the system silently breaks:
- Different `WEAVIATE_CLASS_NAME` → ingestion writes to a collection chat-api never reads
- Different `OPENAI_EMBEDDING_MODEL` → vector dimensions mismatch → retrieval returns garbage
- Different `CACHE_PREFIX` → flush doesn't clear the right keys → stale cache

## Alternatives Considered

### 1. Shared Library for Weaviate + Redis

```
libs/code-shared/
  vector_store/
    weaviate_client.py    ← full client used by both services
  semantic_cache.py       ← full cache used by both services
```

**Pros:** Single source of truth for schema, client code, and cache logic. No risk of constant divergence.

**Cons:**
- `weaviate-client` (~150 MB) and `redis` pulled into auth-api, user-api via transitive dependency
- Changes to `retrieve()` could break `batch_load()` or vice versa
- Versioning: if chat-api needs a new feature but ingestion-worker doesn't, both are blocked until the shared library is updated

**Why rejected:** The dependencies are too heavy and the usage patterns too different.

### 2. Separate Shared Libraries

```
libs/vector-store/    ← Weaviate client only
libs/semantic-cache/  ← Redis cache only
```

**Pros:** Finer-grained dependency management. Services import only what they need.

**Cons:** Still couples the two services — a change to the vector store library requires testing both services. The ingestion-worker's `retrieve()` would still exist as dead code.

**Why rejected:** Marginal improvement over option 1. The ownership problem remains.

### 3. Microservice for Weaviate (Vector Store Service)

```
chat-api → HTTP → vector-store-service → Weaviate
ingestion-worker → HTTP → vector-store-service → Weaviate
```

**Pros:** Single owner of Weaviate access. Schema changes happen in one place.

**Cons:** Adds another service to deploy, monitor, and scale. Adds network latency to every vector search (~5ms). Ingestion batch load would be much slower through HTTP than direct Weaviate client.

**Why rejected:** Over-engineering for two consumers. The added latency and operational complexity outweigh the ownership clarity.

## Consequences

### Positive

- **chat-api and ingestion-worker can evolve independently.** chat-api can optimize its retrieve logic without touching ingestion-worker.
- **Clear ownership.** chat-api owns retrieval; ingestion-worker owns writing. No ambiguity about who maintains what.
- **Minimal dependencies.** auth-api and user-api do not transitively depend on `weaviate-client` or `redis`.
- **Explicit contract.** The shared constants are visible and documented, not hidden in library internals.

### Negative

- **Duplication.** Both services have their own `weaviate_client.py` with overlapping code (connect, close, schema). ~100 lines duplicated.
- **Contract enforcement is manual.** If someone changes `CACHE_PREFIX` in chat-api but not ingestion-worker, the system silently breaks. No compile-time or test-time check.
- **Schema drift risk.** If one service adds a new Weaviate property but the other doesn't, ingestion might write fields that chat-api ignores.

### Mitigation

- Integration tests that run both services against the same Weaviate + Redis instance verify the contract end-to-end
- Configuration values (`WEAVIATE_CLASS_NAME`, `CACHE_EMBED_DIM`, etc.) come from environment variables, which are managed in one place (ConfigMap / `.env` file)

## Related

- [RAG and Ingestion Architecture](../services/rag_and_ingestion.md) — detailed pipeline flow
- [Redis Semantic Cache](../db/redis-semantic-cache.md) — cache implementation details
- [Weaviate Vector Store](../db/weaviate.md) — vector store details
