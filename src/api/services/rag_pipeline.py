"""
RAG pipeline: retrieval, reranking, context building, and LLM generation.
Optional semantic cache: if query embedding matches a cached one above threshold, return cached response.
"""
from typing import Any, Callable, Dict, Iterator, List, Optional

from src.api.services.base_reranker import BaseReranker
from src.core.base_db import BaseVectorStore
from src.core.base_llm import BaseLLM

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_RETRIEVAL_TOP_K = 25
UNKNOWN_SOURCE = "Unknown"


def transform(docs: List[Dict[str, Any]]) -> str:
    """
    Build a formatted context string from retrieved document chunks.

    Args:
        docs: List of dicts with 'text' and 'source' keys.

    Returns:
        Formatted string with numbered chunks and source metadata.
    """
    parts = []
    for i, doc in enumerate(docs, start=1):
        source = doc.get("source", UNKNOWN_SOURCE)
        text = doc.get("text", "")
        part = f"[Chunk {i}]\nSource: {source}\nContent:\n{text}"
        parts.append(part.strip())
    return "\n\n".join(parts)


def answer(
    db: BaseVectorStore,
    llm: BaseLLM,
    first_reranker: BaseReranker,
    second_reranker: BaseReranker,
    query: str,
    *,
    semantic_cache: Optional[Any] = None,
    get_query_embedding: Optional[Callable[[str], List[float]]] = None,
) -> str:
    """
    Run full RAG pipeline: optional semantic cache check, then retrieve, rerank, build context, generate.

    If semantic_cache and get_query_embedding are provided and cache returns a hit (similarity >= threshold),
    the cached response is returned immediately. Otherwise: retrieval -> first rerank -> second (Cohere) rerank -> LLM.
    """
    if semantic_cache and semantic_cache.enabled and get_query_embedding is not None:
        try:
            query_embedding = get_query_embedding(query)
            cached = semantic_cache.get(query_embedding)
            if cached is not None:
                return cached
        except Exception:
            pass

    vec_docs = db.retrieve(query, top_k=DEFAULT_RETRIEVAL_TOP_K)
    filtered_docs = first_reranker.rerank(query, vec_docs)
    final_docs = second_reranker.rerank(query, filtered_docs)
    context = transform(final_docs)
    response = llm.generate(query, context)

    if semantic_cache and semantic_cache.enabled and get_query_embedding is not None:
        try:
            query_embedding = get_query_embedding(query)
            semantic_cache.set(query_embedding, response)
        except Exception:
            pass

    return response


def answer_stream(
    db: BaseVectorStore,
    llm: BaseLLM,
    first_reranker: BaseReranker,
    second_reranker: BaseReranker,
    query: str,
    *,
    semantic_cache: Optional[Any] = None,
    get_query_embedding: Optional[Callable[[str], List[float]]] = None,
) -> Iterator[str]:
    """
    Run RAG pipeline and stream LLM response tokens.
    If semantic cache hits, yields the full cached response as a single chunk then stops.
    Otherwise: retrieval -> rerank -> context -> stream LLM.
    """
    if semantic_cache and semantic_cache.enabled and get_query_embedding is not None:
        try:
            query_embedding = get_query_embedding(query)
            cached = semantic_cache.get(query_embedding)
            if cached is not None:
                yield cached
                return
        except Exception:
            pass

    vec_docs = db.retrieve(query, top_k=DEFAULT_RETRIEVAL_TOP_K)
    filtered_docs = first_reranker.rerank(query, vec_docs)
    final_docs = second_reranker.rerank(query, filtered_docs)
    context = transform(final_docs)
    chunks: List[str] = []
    for chunk in llm.generate_stream(query, context):
        chunks.append(chunk)
        yield chunk

    if semantic_cache and semantic_cache.enabled and get_query_embedding is not None:
        try:
            full_response = "".join(chunks)
            query_embedding = get_query_embedding(query)
            semantic_cache.set(query_embedding, full_response)
        except Exception:
            pass
