"""
RAG pipeline: retrieval, reranking, context building, and LLM generation.
"""
from typing import Any, Dict, Iterator, List

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
) -> str:
    """
    Run full RAG pipeline: retrieve, optionally rerank, build context, generate.

    Args:
        db: Vector store for retrieval.
        llm: LLM for response generation.
        first_reranker: First-stage reranker (currently unused in flow).
        second_reranker: Second-stage reranker (currently unused in flow).
        query: User query.

    Returns:
        Generated answer string.
    """
    vec_docs = db.retrieve(query, top_k=DEFAULT_RETRIEVAL_TOP_K)

    # filtered_docs = first_reranker.rerank(query, vec_docs)
    # final_docs = second_reranker.rerank(query, filtered_docs)

    context = transform(vec_docs)
    return llm.generate(query, context)


def answer_stream(
    db: BaseVectorStore,
    llm: BaseLLM,
    first_reranker: BaseReranker,
    second_reranker: BaseReranker,
    query: str,
) -> Iterator[str]:
    """
    Run RAG pipeline and stream LLM response tokens.
    Retrieval and context building are done once; then chunks are yielded from the LLM.
    """
    vec_docs = db.retrieve(query, top_k=DEFAULT_RETRIEVAL_TOP_K)
    context = transform(vec_docs)
    yield from llm.generate_stream(query, context)
