from typing import Any, Dict, List, Optional

from src.api.services.rag_pipeline import (
    DEFAULT_RETRIEVAL_TOP_K,
    answer,
    answer_stream,
    transform,
)
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

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

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


def test_answer_returns_cached_response_on_semantic_cache_hit():
    """When semantic cache is enabled and get() returns a value, that value is returned without retrieval/LLM."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)
    llm = _FakeLLM()

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True
        get_calls: List[List[float]] = []
        set_calls: List[tuple] = []

        def get(self, embedding: List[float]) -> Optional[str]:
            self.get_calls.append(embedding)
            return "cached-answer"

        def set(self, embedding: List[float], response: str) -> None:
            self.set_calls.append((embedding, response))

    cache = _FakeCache()
    cache.get_calls = []
    cache.set_calls = []
    get_embedding = lambda q: [0.1, 0.2]

    result = answer(
        db=db,
        llm=llm,
        first_reranker=_Dummy(),  # type: ignore[arg-type]
        second_reranker=_Dummy(),  # type: ignore[arg-type]
        query="q",
        semantic_cache=cache,
        get_query_embedding=get_embedding,
    )

    assert result == "cached-answer"
    assert len(cache.get_calls) == 1
    assert cache.get_calls[0] == [0.1, 0.2]
    assert len(cache.set_calls) == 0
    assert len(db.retrieve_calls) == 0
    assert len(llm.calls) == 0


def test_answer_continues_on_cache_lookup_exception():
    """When cache is enabled but get_query_embedding or cache.get raises, pipeline still runs."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)
    llm = _FakeLLM()

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True
        set_calls: List[tuple] = []

        def get(self, embedding: List[float]) -> Optional[str]:
            raise ValueError("embedding service down")

        def set(self, embedding: List[float], response: str) -> None:
            self.set_calls.append((embedding, response))

    cache = _FakeCache()
    cache.set_calls = []
    get_embedding = lambda q: [0.1, 0.2]

    result = answer(
        db=db,
        llm=llm,
        first_reranker=_Dummy(),  # type: ignore[arg-type]
        second_reranker=_Dummy(),  # type: ignore[arg-type]
        query="q",
        semantic_cache=cache,
        get_query_embedding=get_embedding,
    )

    assert result == "fake-answer-for:q"
    assert len(cache.set_calls) == 1


def test_answer_stores_response_in_semantic_cache_on_miss():
    """When cache is enabled but miss, full pipeline runs and cache.set() is called."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)
    llm = _FakeLLM()

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True
        set_calls: List[tuple] = []

        def get(self, embedding: List[float]) -> Optional[str]:
            return None

        def set(self, embedding: List[float], response: str) -> None:
            self.set_calls.append((embedding, response))

    cache = _FakeCache()
    cache.set_calls = []
    get_embedding = lambda q: [0.1, 0.2]

    result = answer(
        db=db,
        llm=llm,
        first_reranker=_Dummy(),  # type: ignore[arg-type]
        second_reranker=_Dummy(),  # type: ignore[arg-type]
        query="q",
        semantic_cache=cache,
        get_query_embedding=get_embedding,
    )

    assert result == "fake-answer-for:q"
    assert len(cache.set_calls) == 1
    assert cache.set_calls[0][1] == "fake-answer-for:q"


def test_answer_returns_response_when_cache_set_raises():
    """When cache.set() raises, answer still returns the generated response."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)
    llm = _FakeLLM()

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True

        def get(self, embedding: List[float]) -> Optional[str]:
            return None

        def set(self, embedding: List[float], response: str) -> None:
            raise RuntimeError("redis down")

    result = answer(
        db=db,
        llm=llm,
        first_reranker=_Dummy(),  # type: ignore[arg-type]
        second_reranker=_Dummy(),  # type: ignore[arg-type]
        query="q",
        semantic_cache=_FakeCache(),
        get_query_embedding=lambda q: [0.0],
    )
    assert result == "fake-answer-for:q"


def test_answer_stream_yields_cached_response_on_hit():
    """Stream path: cache hit yields cached string and returns."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)

    class _FakeLLMStream(BaseLLM):
        def generate(self, query: str, context: str) -> str:
            return ""

        def generate_stream(self, query: str, context: str):
            yield "a"
            yield "b"

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True

        def get(self, embedding: List[float]) -> Optional[str]:
            return "stream-cached"

        def set(self, embedding: List[float], response: str) -> None:
            pass

    out = list(
        answer_stream(
            db=db,
            llm=_FakeLLMStream(),
            first_reranker=_Dummy(),  # type: ignore[arg-type]
            second_reranker=_Dummy(),  # type: ignore[arg-type]
            query="q",
            semantic_cache=_FakeCache(),
            get_query_embedding=lambda q: [0.0],
        )
    )
    assert out == ["stream-cached"]
    assert len(db.retrieve_calls) == 0


def test_answer_stream_stores_in_cache_after_streaming():
    """Stream path: cache miss runs pipeline and cache.set() is called with full response."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)

    class _FakeLLMStream(BaseLLM):
        def generate(self, query: str, context: str) -> str:
            return ""

        def generate_stream(self, query: str, context: str):
            yield "hello"
            yield " world"

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True
        set_calls: List[tuple] = []

        def get(self, embedding: List[float]) -> Optional[str]:
            return None

        def set(self, embedding: List[float], response: str) -> None:
            self.set_calls.append((embedding, response))

    cache = _FakeCache()
    cache.set_calls = []
    out = list(
        answer_stream(
            db=db,
            llm=_FakeLLMStream(),
            first_reranker=_Dummy(),  # type: ignore[arg-type]
            second_reranker=_Dummy(),  # type: ignore[arg-type]
            query="q",
            semantic_cache=cache,
            get_query_embedding=lambda q: [0.0],
        )
    )
    assert out == ["hello", " world"]
    assert len(cache.set_calls) == 1
    assert cache.set_calls[0][1] == "hello world"


def test_answer_stream_continues_on_cache_get_exception():
    """When cache get raises, stream runs full pipeline and yields chunks."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)

    class _FakeLLMStream(BaseLLM):
        def generate(self, query: str, context: str) -> str:
            return ""

        def generate_stream(self, query: str, context: str):
            yield "a"

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True

        def get(self, embedding: List[float]) -> Optional[str]:
            raise ValueError("cache error")

        def set(self, embedding: List[float], response: str) -> None:
            pass

    out = list(
        answer_stream(
            db=db,
            llm=_FakeLLMStream(),
            first_reranker=_Dummy(),  # type: ignore[arg-type]
            second_reranker=_Dummy(),  # type: ignore[arg-type]
            query="q",
            semantic_cache=_FakeCache(),
            get_query_embedding=lambda q: [0.0],
        )
    )
    assert out == ["a"]


def test_answer_stream_yields_all_when_cache_set_raises():
    """When cache.set raises after streaming, all chunks were already yielded."""
    docs = [{"text": "x", "source": "a.pdf"}]
    db = _FakeVectorStore(docs)

    class _FakeLLMStream(BaseLLM):
        def generate(self, query: str, context: str) -> str:
            return ""

        def generate_stream(self, query: str, context: str):
            yield "x"

    class _Dummy:
        def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return docs

    class _FakeCache:
        enabled = True

        def get(self, embedding: List[float]) -> Optional[str]:
            return None

        def set(self, embedding: List[float], response: str) -> None:
            raise RuntimeError("redis down")

    out = list(
        answer_stream(
            db=db,
            llm=_FakeLLMStream(),
            first_reranker=_Dummy(),  # type: ignore[arg-type]
            second_reranker=_Dummy(),  # type: ignore[arg-type]
            query="q",
            semantic_cache=_FakeCache(),
            get_query_embedding=lambda q: [0.0],
        )
    )
    assert out == ["x"]