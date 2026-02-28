"""Vector store (Weaviate) for ingestion-worker."""

from src.vector_store.base import BaseVectorStore
from src.vector_store.weaviate_client import WeaviateClient

__all__ = ["BaseVectorStore", "WeaviateClient"]
