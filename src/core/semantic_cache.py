"""
Semantic cache for RAG: store (query_embedding, LLM_response) in Redis with vector similarity lookup.
Uses the same embed model as Weaviate; if a cached query embedding is similar enough, return cached response.
Requires Redis Stack (RediSearch with vector support).
"""
import logging
import uuid
from typing import Any, List, Optional

import numpy as np
import redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from src.core.config import settings

logger = logging.getLogger(__name__)

CACHE_PREFIX = "rag_cache:"
INDEX_NAME = "rag_cache_idx"


def _embedding_to_bytes(embedding: List[float]) -> bytes:
    """Convert list of floats to FLOAT32 bytes for Redis."""
    return np.array(embedding, dtype=np.float32).tobytes()


def _cosine_distance_to_similarity(score_str: str) -> float:
    """RediSearch COSINE returns distance; similarity = 1 - distance."""
    try:
        distance = float(score_str)
        return 1.0 - distance
    except (TypeError, ValueError):
        return 0.0


class SemanticCache:
    """
    Semantic cache using Redis Stack vector search.
    Embeddings must match the Weaviate embed model (same dimension and model).
    """

    def __init__(
        self,
        redis_url: str = "",
        ttl_seconds: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        embed_dim: Optional[int] = None,
    ) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_SECONDS
        self.similarity_threshold = (
            similarity_threshold if similarity_threshold is not None else settings.CACHE_SIMILARITY_THRESHOLD
        )
        self.embed_dim = embed_dim or settings.CACHE_EMBED_DIM
        self._client: Optional[redis.Redis] = None
        self._enabled = bool(self.redis_url.strip())

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _client_or_raise(self) -> redis.Redis:
        if not self._enabled:
            raise RuntimeError("Semantic cache is disabled (no REDIS_URL).")
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=False)
        return self._client

    def _ensure_index(self, r: redis.Redis) -> None:
        try:
            r.ft(INDEX_NAME).info()
            return
        except redis.exceptions.ResponseError:
            pass
        schema = (
            VectorField(
                "vector",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.embed_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
            TextField("response"),
        )
        definition = IndexDefinition(prefix=[CACHE_PREFIX], index_type=IndexType.HASH)
        r.ft(INDEX_NAME).create_index(fields=schema, definition=definition)
        logger.info("Created Redis semantic cache index %s", INDEX_NAME)

    def get(self, query_embedding: List[float]) -> Optional[str]:
        """
        Look up cache by query embedding. If best match has similarity >= threshold, return cached response.
        """
        if not self._enabled:
            return None
        try:
            r = self._client_or_raise()
            self._ensure_index(r)
            vec_bytes = _embedding_to_bytes(query_embedding)
            q = (
                Query("*=>[KNN 1 @vector $vec AS score]")
                .return_fields("response", "score")
                .sort_by("score")
                .paging(0, 1)
                .dialect(2)
            )
            results = r.ft(INDEX_NAME).search(q, query_params={"vec": vec_bytes})
            if not results.docs:
                return None
            doc = results.docs[0]
            score_str = getattr(doc, "score", None) or getattr(doc, "payload", {}).get("score")
            if score_str is None:
                return None
            similarity = _cosine_distance_to_similarity(str(score_str))
            if similarity < self.similarity_threshold:
                return None
            response = getattr(doc, "response", None)
            if response is None:
                return None
            if isinstance(response, bytes):
                response = response.decode("utf-8", errors="replace")
            return response
        except Exception as e:
            logger.warning("Semantic cache get failed: %s", e)
            return None

    def set(self, query_embedding: List[float], response: str) -> None:
        """Store (query_embedding, response) in Redis with TTL."""
        if not self._enabled:
            return
        try:
            r = self._client_or_raise()
            self._ensure_index(r)
            key = f"{CACHE_PREFIX}{uuid.uuid4().hex}"
            vec_bytes = _embedding_to_bytes(query_embedding)
            # RediSearch indexes HASH; we need to store as string for response (binary-safe)
            r.hset(key, mapping={"vector": vec_bytes, "response": response})
            r.expire(key, self.ttl_seconds)
        except Exception as e:
            logger.warning("Semantic cache set failed: %s", e)

    def flush(self) -> None:
        """Remove all cache entries (e.g. after vector store update)."""
        if not self._enabled:
            return
        try:
            r = self._client_or_raise()
            count = 0
            for key in r.scan_iter(match=f"{CACHE_PREFIX}*", count=100):
                r.delete(key)
                count += 1
            try:
                r.ft(INDEX_NAME).dropindex(delete_documents=False)
            except redis.exceptions.ResponseError:
                pass
            logger.info("Semantic cache flushed (%s keys removed).", count)
        except Exception as e:
            logger.warning("Semantic cache flush failed: %s", e)

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
