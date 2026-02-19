from typing import Any, Dict, List

from src.api.services.rag_pipeline import DEFAULT_RETRIEVAL_TOP_K, answer, transform
from src.core.base_db import BaseVectorStore
from src.core.base_llm import BaseLLM


class _FakeVectorStore(BaseVectorStore):
    def __init__(self, docs: List[Dict[str, Any]]) -> None:
        self._docs = docs
        self.retrieve_calls: List[Dict[str, Any]] = []

    def connect(self) -> None:  # pragma: no cover - not used here
        return None

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        self.retrieve_calls.append({"query": query, "top_k": top_k})
        return self._docs[:top_k]

    def batch_load(self, items: List[Dict[str, Any]]) -> None:  # pragma: no cover
        self._docs.extend(items)

    def close(self) -> None:  # pragma: no cover
        return None


class _FakeLLM(BaseLLM):
    def __init__(self) -> None:
        self.calls: List[Dict[str, str]] = []

    def generate(self, query: str, context: str) -> str:
        self.calls.append({"query": query, "context": context})
        return f"fake-answer-for:{query}"


def test_transform_builds_numbered_chunks():
    docs = [
        {"text": "chunk one", "source": "a.pdf"},
        {"text": "chunk two", "source": "b.pdf"},
    ]

    result = transform(docs)

    assert "[Chunk 1]" in result
    assert "Source: a.pdf" in result
    assert "chunk one" in result
    assert "[Chunk 2]" in result
    assert "Source: b.pdf" in result
    assert "chunk two" in result


def test_transform_handles_missing_source_and_text():
    docs = [{}]

    result = transform(docs)

    assert "Unknown" in result
    # Empty text should still render without crashing
    assert "Content:" in result


def test_answer_calls_vector_store_and_llm_in_order():
    docs = [
        {"text": "some law", "source": "law.pdf"},
        {"text": "more law", "source": "law2.pdf"},
    ]
    db = _FakeVectorStore(docs)
    llm = _FakeLLM()

    # rerankers are currently unused in the pipeline; pass simple sentinels
    class _Dummy:
        ...

    result = answer(
        db=db,
        llm=llm,
        first_reranker=_Dummy(),  # type: ignore[arg-type]
        second_reranker=_Dummy(),  # type: ignore[arg-type]
        query="What is the law?",
    )

    # Check vector store was queried with default top_k
    assert db.retrieve_calls, "retrieve() should be called at least once"
    call = db.retrieve_calls[0]
    assert call["query"] == "What is the law?"
    assert call["top_k"] == DEFAULT_RETRIEVAL_TOP_K

    # Check LLM was called with correctly built context
    assert llm.calls, "generate() should be called at least once"
    llm_call = llm.calls[0]
    assert llm_call["query"] == "What is the law?"
    assert "some law" in llm_call["context"]
    assert "more law" in llm_call["context"]

    # And that answer returns the LLM output
    assert result == "fake-answer-for:What is the law?"