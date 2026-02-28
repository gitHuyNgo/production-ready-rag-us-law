"""Abstract base for vector store."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseVectorStore(ABC):
    """Interface for vector store operations."""

    @abstractmethod
    def connect(self) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        pass  # pragma: no cover

    @abstractmethod
    def batch_load(self, items: List[Dict[str, Any]]) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def close(self) -> None:
        pass  # pragma: no cover
