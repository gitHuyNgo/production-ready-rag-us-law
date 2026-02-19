from typing import Any, Dict, List
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so 'src' is importable when running tests
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import app
from src.api.services.base_reranker import BaseReranker
from src.core.base_db import BaseVectorStore
from src.core.base_llm import BaseLLM


class InMemoryVectorStore(BaseVectorStore):
    """Simple in-memory vector store for tests."""

    def __init__(self, docs: List[Dict[str, Any]] | None = None) -> None:
        self._docs = docs or []

    def connect(self) -> None:  # pragma: no cover - no-op
        return None

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        # Ignore similarity, just truncate
        return self._docs[:top_k]

    def batch_load(self, items: List[Dict[str, Any]]) -> None:
        self._docs.extend(items)

    def close(self) -> None:  # pragma: no cover - no-op
        return None


class DummyLLM(BaseLLM):
    """Deterministic LLM for tests."""

    def generate(self, query: str, context: str) -> str:
        return f"ANSWER to '{query}' with {len(context)} chars of context"


class PassthroughReranker(BaseReranker):
    """Reranker that just returns docs unchanged."""

    def __init__(self, top_k: int = 10) -> None:
        self.top_k = top_k

    def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return docs[: self.top_k]


@pytest.fixture
def sample_docs() -> List[Dict[str, Any]]:
    return [
        {"text": "First legal chunk", "source": "doc1.pdf"},
        {"text": "Second legal chunk", "source": "doc2.pdf"},
    ]


@pytest.fixture
def vector_store(sample_docs: List[Dict[str, Any]]) -> InMemoryVectorStore:
    store = InMemoryVectorStore(sample_docs)
    store.connect()
    return store


@pytest.fixture
def llm() -> DummyLLM:
    return DummyLLM()


@pytest.fixture
def reranker() -> PassthroughReranker:
    return PassthroughReranker()


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient with in-memory dependencies."""
    # Override app state with test doubles
    app.state.db = InMemoryVectorStore(
        [
            {"text": "Test law chunk", "source": "test.pdf"},
        ]
    )
    app.state.llm = DummyLLM()
    app.state.first_reranker = PassthroughReranker()
    app.state.second_reranker = PassthroughReranker()

    return TestClient(app)