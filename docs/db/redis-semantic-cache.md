# Redis Semantic Cache

**Owners**: chat-api (get/set, vector index), ingestion-worker (flush only)

**Purpose**: Cache RAG responses by query embedding similarity to reduce LLM calls and latency.

## Chat API

- **Location**: `app/chat-api/src/semantic_cache.py`.
- **Usage**: For each query, the pipeline computes the query embedding and checks Redis (RediSearch vector index) for a cached response whose embedding is within a configured similarity threshold. On cache hit, the cached response is returned; on miss, normal RAG + LLM runs and the result is stored with the query embedding.
- **Configuration**: Redis URL, TTL, similarity threshold, and embed dimension (e.g. `REDIS_URL`, `CACHE_TTL_SECONDS`, `CACHE_SIMILARITY_THRESHOLD`, `CACHE_EMBED_DIM`). Disabled when Redis URL is empty.

## Ingestion Worker

- **Location**: `app/ingestion-worker/src/semantic_cache.py`.
- **Usage**: Flush-only. After loading new documents into Weaviate, the worker clears Redis keys under the same prefix/index used by chat-api so that subsequent chat queries do not hit stale cached answers. Uses the same key prefix and index name as chat-api for consistency.

## Deployment

- Redis Stack (with RediSearch) is used for vector similarity. Docker Compose typically runs `redis/redis-stack`; chat-api and ingestion-worker use the same `REDIS_URL` in shared environments.
