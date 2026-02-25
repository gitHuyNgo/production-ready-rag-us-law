"""Unit tests for chat router helpers."""
from unittest.mock import MagicMock

from src.api.routers.chat_router import _get_query_embedding_fn


def test_get_query_embedding_fn_returns_none_when_embed_model_is_none():
    assert _get_query_embedding_fn(None) is None


def test_get_query_embedding_fn_returns_callable_that_calls_get_text_embedding():
    mock_embed = MagicMock()
    mock_embed.get_text_embedding.return_value = [0.1, 0.2]
    fn = _get_query_embedding_fn(mock_embed)
    assert fn is not None
    assert callable(fn)
    result = fn("hello")
    assert result == [0.1, 0.2]
    mock_embed.get_text_embedding.assert_called_once_with("hello")
