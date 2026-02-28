"""Vector store (Weaviate) for chat-api."""

from src.vector_store.base import BaseVectorStore
from src.vector_store.weaviate_client import WeaviateClient

__all__ = ["BaseVectorStore", "WeaviateClient"]
