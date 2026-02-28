"""
Minimal semantic cache for ingestion-worker: flush Redis RAG cache after ingest.
Uses same key prefix/index as chat-api so flush clears chat-api's cache.
"""
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)

CACHE_PREFIX = "rag_cache:"
INDEX_NAME = "rag_cache_idx"


class SemanticCache:
    """Flush-only semantic cache (ingestion-worker clears cache after ingest)."""

    def __init__(
        self,
        redis_url: str = "",
        ttl_seconds: int = 86400,
        similarity_threshold: float = 0.95,
        embed_dim: int = 3072,
    ) -> None:
        self.redis_url = redis_url or ""
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

    def flush(self) -> None:
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
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
