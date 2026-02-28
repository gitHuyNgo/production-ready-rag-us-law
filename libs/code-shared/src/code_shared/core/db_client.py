"""
Weaviate vector store client for document storage and retrieval.
Caller passes config (each service has its own settings).
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import weaviate
from llama_index.embeddings.openai import OpenAIEmbedding
from weaviate.classes.query import MetadataQuery

from code_shared.core.base_db import BaseVectorStore
from code_shared.core.schema import init_schema


def _host_port_from_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port if parsed.port is not None else 8080
    return host, port


class WeaviateClient(BaseVectorStore):
    """Weaviate-backed vector store with OpenAI embeddings."""

    def __init__(
        self,
        weaviate_url: str,
        weaviate_class_name: str,
        openai_api_key: str,
        openai_embedding_model: str = "text-embedding-3-large",
    ) -> None:
        self.weaviate_url = weaviate_url
        self.class_name = weaviate_class_name
        self.embed_model = OpenAIEmbedding(
            api_key=openai_api_key,
            model=openai_embedding_model,
        )
        self.client: Optional[weaviate.WeaviateClient] = None

    def connect(self) -> weaviate.WeaviateClient:
        host, port = _host_port_from_url(self.weaviate_url)
        self.client = weaviate.connect_to_local(host=host, port=port)
        return self.client

    def initialize_schema(self, recreate: bool = False) -> None:
        if self.client is None:
            raise RuntimeError("Connect before calling initialize_schema")
        init_schema(self.client, self.class_name, recreate=recreate)

    def batch_load(self, items: List[Dict[str, Any]]) -> None:
        collection = self.client.collections.use(self.class_name)
        with collection.batch.dynamic() as batch:
            for item in items:
                vector = self.embed_model.get_text_embedding(item["text"])
                batch.add_object(properties=item, vector=vector)

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_vector = self.embed_model.get_text_embedding(query)
        collection = self.client.collections.use(self.class_name)
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )
        return [obj.properties for obj in response.objects]

    def close(self) -> None:
        if self.client:
            self.client.close()
