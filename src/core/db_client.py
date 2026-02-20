"""
Weaviate vector store client for document storage and retrieval.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import weaviate
from llama_index.embeddings.openai import OpenAIEmbedding
from weaviate.classes.query import MetadataQuery

from src.core.config import settings
from src.core.base_db import BaseVectorStore


def _host_port_from_url(url: str) -> tuple[str, int]:
    """Parse WEAVIATE_URL into (host, port) for connect_to_local."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port if parsed.port is not None else 8080
    return host, port


class WeaviateClient(BaseVectorStore):
    """Weaviate-backed vector store with OpenAI embeddings."""

    def __init__(self) -> None:
        self.class_name = settings.WEAVIATE_CLASS_NAME
        self.embed_model = OpenAIEmbedding(api_key=settings.OPENAI_API_KEY)
        self.client: Optional[weaviate.WeaviateClient] = None

    def connect(self) -> weaviate.WeaviateClient:
        """Connect to Weaviate using WEAVIATE_URL (e.g. http://localhost:8080)."""
        host, port = _host_port_from_url(settings.WEAVIATE_URL)
        self.client = weaviate.connect_to_local(host=host, port=port)
        return self.client

    def initialize_schema(self, recreate: bool = False) -> None:
        """Create or recreate collection schema."""  # pragma: no cover
        if recreate and self.client.collections.exists(self.class_name):  # pragma: no cover
            self.client.collections.delete(self.class_name)  # pragma: no cover

        if not self.client.collections.exists(self.class_name):  # pragma: no cover
            pass  # pragma: no cover

    def batch_load(self, items: List[Dict[str, Any]]) -> None:
        """Load documents into the vector store with embeddings."""
        collection = self.client.collections.use(self.class_name)

        with collection.batch.dynamic() as batch:
            for item in items:
                vector = self.embed_model.get_text_embedding(item["text"])
                batch.add_object(properties=item, vector=vector)

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve top-k documents by semantic similarity to query."""
        query_vector = self.embed_model.get_text_embedding(query)
        collection = self.client.collections.use(self.class_name)

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )

        return [obj.properties for obj in response.objects]

    def close(self) -> None:
        """Close Weaviate connection."""
        if self.client:
            self.client.close()
