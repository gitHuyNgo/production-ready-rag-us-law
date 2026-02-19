"""
Abstract base class for LLM implementations.
"""
from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Interface for LLM response generation."""

    @abstractmethod
    def generate(self, query: str, context: str) -> str:
        """
        Generate an answer from query and context.

        Args:
            query: User question.
            context: Retrieved document context.

        Returns:
            Generated answer string.
        """
        pass  # pragma: no cover
