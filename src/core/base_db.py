"""
Abstract base class for vector store implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseVectorStore(ABC):
    """Interface for vector store operations."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the vector store."""
        pass

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve top-k documents by similarity to query.

        Returns:
            List of document dicts (e.g. {"text": ..., "source": ...}).
        """
        pass

    @abstractmethod
    def batch_load(self, items: List[Dict[str, Any]]) -> None:
        """Load a batch of items into the vector store."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection and release resources."""
        pass
