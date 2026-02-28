"""Weaviate client for ingestion-worker (write + schema)."""
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import weaviate
from llama_index.embeddings.openai import OpenAIEmbedding

from src.vector_store.base import BaseVectorStore
from src.vector_store.schema import init_schema


def _host_port_from_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port if parsed.port is not None else 8080
    return host, port


class WeaviateClient(BaseVectorStore):
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
        raise NotImplementedError("Ingestion-worker only writes to Weaviate")

    def close(self) -> None:
        if self.client:
            self.client.close()
