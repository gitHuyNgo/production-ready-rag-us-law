"""
Abstract base class for reranker implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseReranker(ABC):
    """Interface for reranking retrieved documents by relevance to a query."""

    @abstractmethod
    def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank documents by relevance to the query.

        Args:
            query: User query string.
            docs: List of document dicts (e.g. {"text": ..., "source": ...}).

        Returns:
            Reranked list of documents (possibly reordered and/or truncated).
        """
        pass
