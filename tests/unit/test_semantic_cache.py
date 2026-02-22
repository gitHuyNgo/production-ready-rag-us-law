"""Unit tests for semantic cache (mocked Redis)."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.core.semantic_cache import (
    SemanticCache,
    _cosine_distance_to_similarity,
    _embedding_to_bytes,
)


def test_embedding_to_bytes():
    out = _embedding_to_bytes([1.0, 0.0, -1.0])
    assert isinstance(out, bytes)
    assert len(out) == 3 * 4  # 3 floats * 4 bytes


def test_cosine_distance_to_similarity():
    assert _cosine_distance_to_similarity("0.0") == 1.0
    assert _cosine_distance_to_similarity("0.2") == 0.8
    assert _cosine_distance_to_similarity("1.0") == 0.0
    assert _cosine_distance_to_similarity("invalid") == 0.0
    assert _cosine_distance_to_similarity(None) == 0.0


def _cache_settings(
    REDIS_URL="",
    CACHE_TTL_SECONDS=86400,
    CACHE_SIMILARITY_THRESHOLD=0.95,
    CACHE_EMBED_DIM=1536,
    **kwargs,
):
    return SimpleNamespace(
        REDIS_URL=REDIS_URL,
        CACHE_TTL_SECONDS=CACHE_TTL_SECONDS,
        CACHE_SIMILARITY_THRESHOLD=CACHE_SIMILARITY_THRESHOLD,
        CACHE_EMBED_DIM=CACHE_EMBED_DIM,
        **kwargs,
    )


def test_semantic_cache_disabled_when_redis_url_empty(monkeypatch):
    monkeypatch.setattr("src.core.semantic_cache.settings", _cache_settings(REDIS_URL=""))
    cache = SemanticCache(redis_url="")
    assert cache.enabled is False
    assert cache.get([0.1] * 1536) is None
    cache.set([0.1] * 1536, "resp")
    cache.flush()
    cache.close()


def test_semantic_cache_enabled_when_redis_url_set(monkeypatch):
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://localhost:6379"),
    )
    cache = SemanticCache(redis_url="redis://localhost:6379")
    assert cache.enabled is True


def test_semantic_cache_client_or_raise_when_disabled(monkeypatch):
    monkeypatch.setattr("src.core.semantic_cache.settings", _cache_settings(REDIS_URL=""))
    cache = SemanticCache(redis_url="")
    with pytest.raises(RuntimeError, match="disabled"):
        cache._client_or_raise()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_get_hit(mock_from_url, monkeypatch):
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://localhost:6379", CACHE_EMBED_DIM=2, CACHE_SIMILARITY_THRESHOLD=0.9),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    doc = SimpleNamespace(score="0.05", response=b"cached text")
    mock_ft.search.return_value = SimpleNamespace(docs=[doc])
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://localhost:6379")
    result = cache.get([0.1, 0.2])

    assert result == "cached text"
    mock_ft.search.assert_called_once()
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_get_miss_no_docs(mock_from_url, monkeypatch):
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    mock_ft.search.return_value = SimpleNamespace(docs=[])
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    result = cache.get([0.1, 0.2])

    assert result is None
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_get_returns_none_when_score_missing(mock_from_url, monkeypatch):
    """When doc has no score attribute, get returns None."""
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    doc = SimpleNamespace(response=b"x")  # no score
    mock_ft.search.return_value = SimpleNamespace(docs=[doc])
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    result = cache.get([0.1, 0.2])
    assert result is None
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_get_returns_none_when_response_missing(mock_from_url, monkeypatch):
    """When doc has score but no response, get returns None."""
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    doc = SimpleNamespace(score="0.05")  # no response
    mock_ft.search.return_value = SimpleNamespace(docs=[doc])
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    result = cache.get([0.1, 0.2])
    assert result is None
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_get_below_threshold(mock_from_url, monkeypatch):
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_SIMILARITY_THRESHOLD=0.95, CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    doc = SimpleNamespace(score="0.2", response=b"x")  # similarity 0.8 < 0.95
    mock_ft.search.return_value = SimpleNamespace(docs=[doc])
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    result = cache.get([0.1, 0.2])

    assert result is None
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_set(mock_from_url, monkeypatch):
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_TTL_SECONDS=100, CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    cache.set([0.1, 0.2], "my response")

    mock_r.hset.assert_called_once()
    mapping = mock_r.hset.call_args[1]["mapping"]
    assert mapping["response"] == "my response"
    mock_r.expire.assert_called_once()
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_ensure_index_creates_when_missing(mock_from_url, monkeypatch):
    import redis.exceptions

    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.side_effect = redis.exceptions.ResponseError("no index")
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    cache._ensure_index(mock_r)

    mock_ft.create_index.assert_called_once()
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_flush(mock_from_url, monkeypatch):
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_r.scan_iter.return_value = ["rag_cache:k1", "rag_cache:k2"]
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    cache.flush()

    assert mock_r.delete.call_count == 2
    mock_ft.dropindex.assert_called_once_with(delete_documents=False)
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_flush_ignores_dropindex_error(mock_from_url, monkeypatch):
    """When dropindex raises ResponseError (e.g. index already gone), flush still completes."""
    import redis.exceptions

    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_r.scan_iter.return_value = []
    mock_ft.dropindex.side_effect = redis.exceptions.ResponseError("no index")
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    cache.flush()

    cache.close()


def test_semantic_cache_init_uses_custom_params(monkeypatch):
    monkeypatch.setattr("src.core.semantic_cache.settings", _cache_settings(REDIS_URL=""))
    cache = SemanticCache(
        redis_url="",
        ttl_seconds=100,
        similarity_threshold=0.88,
        embed_dim=10,
    )
    assert cache.ttl_seconds == 100
    assert cache.similarity_threshold == 0.88
    assert cache.embed_dim == 10


def test_semantic_cache_close_idempotent():
    cache = SemanticCache(redis_url="")
    cache.close()
    cache.close()

def test_semantic_cache_close_handles_client_close_error():
    cache = SemanticCache(redis_url="")
    cache._client = MagicMock()
    cache._client.close.side_effect = Exception("close failed")
    cache.close()
    assert cache._client is None


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_get_handles_redis_error(mock_from_url, monkeypatch):
    """When Redis/search raises, get returns None (exception path covered)."""
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    mock_ft.search.side_effect = Exception("redis error")
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    result = cache.get([0.1, 0.2])

    assert result is None
    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_set_handles_redis_error(mock_from_url, monkeypatch):
    """When hset/expire raises, set catches and does not raise."""
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_TTL_SECONDS=100, CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_ft = MagicMock()
    mock_r.ft.return_value = mock_ft
    mock_ft.info.return_value = {}
    mock_r.hset.side_effect = Exception("redis error")
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    cache.set([0.1, 0.2], "text")

    cache.close()


@patch("src.core.semantic_cache.redis.from_url")
def test_semantic_cache_flush_handles_redis_error(mock_from_url, monkeypatch):
    """When flush hits an error, it catches and does not raise."""
    monkeypatch.setattr(
        "src.core.semantic_cache.settings",
        _cache_settings(REDIS_URL="redis://x", CACHE_EMBED_DIM=2),
    )
    mock_r = MagicMock()
    mock_r.ft.return_value = MagicMock()
    mock_r.scan_iter.side_effect = Exception("redis error")
    mock_from_url.return_value = mock_r

    cache = SemanticCache(redis_url="redis://x")
    cache.flush()

    cache.close()
