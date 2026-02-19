from typing import Any, Dict, List
import os
from types import SimpleNamespace

import pytest

from src.api.services import reranker_client as rc_module
from src.api.services.reranker_client import BM25Reranker, CohereReranker


def _make_docs(texts: List[str]) -> List[Dict[str, Any]]:
    return [{"text": t, "source": f"s{i}.pdf"} for i, t in enumerate(texts)]


def test_bm25_reranker_returns_empty_on_no_docs():
    reranker = BM25Reranker(top_k=5)

    result = reranker.rerank("query", [])

    assert result == []


def test_bm25_reranker_respects_top_k():
    docs = _make_docs(
        [
            "law about contracts",
            "criminal law statute",
            "civil procedure rules",
        ]
    )
    reranker = BM25Reranker(top_k=2)

    ranked = reranker.rerank("law", docs)

    assert len(ranked) == 2
    # Ensure returned docs are subset of original docs
    assert set(map(lambda d: d["text"], ranked)).issubset(
        set(map(lambda d: d["text"], docs))
    )


def test_cohere_reranker_raises_without_api_key(monkeypatch: pytest.MonkeyPatch):
    fake_settings = SimpleNamespace(COHERE_API_KEY="")
    monkeypatch.setattr(
        rc_module,
        "settings",
        fake_settings,
    )

    with pytest.raises(ValueError):
        CohereReranker()


def test_cohere_reranker_returns_empty_on_no_docs(monkeypatch: pytest.MonkeyPatch):
    class _FakeClient:
        def rerank(self, *args, **kwargs):
            raise AssertionError("Should not be called when docs is empty")

    fake_settings = SimpleNamespace(COHERE_API_KEY="key")
    monkeypatch.setattr(
        rc_module,
        "settings",
        fake_settings,
    )
    # Replace the whole `cohere` object used in the module with a simple
    # namespace exposing `ClientV2` so `__init__` succeeds without network.
    monkeypatch.setattr(rc_module, "cohere", SimpleNamespace(ClientV2=lambda key: _FakeClient()))

    reranker = CohereReranker(top_k=3)

    result = reranker.rerank("query", docs=[])

    assert result == []


def test_cohere_reranker_reranks_with_fake_client(monkeypatch: pytest.MonkeyPatch):
    class _FakeResponse:
        def __init__(self):
            self.results = [SimpleNamespace(index=1, relevance_score=0.9)]

    class _FakeClient:
        def rerank(self, *args, **kwargs):
            return _FakeResponse()

    fake_settings = SimpleNamespace(COHERE_API_KEY="realish-key")
    monkeypatch.setattr(
        rc_module,
        "settings",
        fake_settings,
    )
    monkeypatch.setattr(rc_module, "cohere", SimpleNamespace(ClientV2=lambda key: _FakeClient()))

    docs = _make_docs(["a", "b"])
    reranker = CohereReranker(top_k=1)

    ranked = reranker.rerank("a", docs)

    assert len(ranked) == 1
    assert "rerank_score" in ranked[0]


@pytest.mark.external
def test_cohere_reranker_live_call_when_key_present():
    """Smoke test hitting live Cohere rerank API when a real key is configured."""
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key or api_key == "dummy":
        pytest.skip("COHERE_API_KEY not set to a real key")

    docs = _make_docs(["foo", "bar"])
    reranker = CohereReranker(top_k=1)

    ranked = reranker.rerank("foo", docs)

    assert len(ranked) == 1