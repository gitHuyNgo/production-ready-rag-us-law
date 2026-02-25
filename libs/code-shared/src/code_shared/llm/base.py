"""
Abstract base class for LLM implementations.
"""
from abc import ABC, abstractmethod
from typing import Iterator


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

    def generate_stream(self, query: str, context: str) -> Iterator[str]:
        """
        Stream answer tokens from query and context.
        Default implementation yields the full response from generate() as one chunk.
        Override to stream token-by-token.

        Args:
            query: User question.
            context: Retrieved document context.

        Yields:
            Content chunks (e.g. single tokens or short strings).
        """
        full = self.generate(query, context)
        if full:
            yield full
