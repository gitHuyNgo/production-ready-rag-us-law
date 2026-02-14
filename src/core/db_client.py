import weaviate
from typing import List, Dict, Any
from weaviate.classes.query import MetadataQuery
from llama_index.embeddings.openai import OpenAIEmbedding
from src.core.config import settings
from .base_db import BaseVectorStore


class WeaviateClient(BaseVectorStore):
    def __init__(self):
        self.class_name = settings.WEAVIATE_CLASS_NAME
        self.embed_model = OpenAIEmbedding(api_key=settings.OPENAI_API_KEY)
        self.client = None
    
    def connect(self):
        self.client = weaviate.connect_to_local()
        return self.client
    
    def initialize_schema(self, recreate: bool = False):
        if recreate and self.client.collections.exists(self.class_name):
            self.client.collections.delete(self.class_name)
        
        if not self.client.collections.exists(self.class_name):
            pass
    
    def batch_load(self, items: List[Dict[str, Any]]):
        collection = self.client.collections.use(self.class_name)
        
        with collection.batch.dynamic() as batch:
            for item in items:
                vector = self.embed_model.get_text_embedding(item["text"])
                batch.add_object(
                    properties=item,
                    vector=vector
                )

    def retrieve(self, query, top_k = 10):
        query_vector = self.embed_model.get_text_embedding(query)
        collection = self.client.collections.use(self.class_name)
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )
        return [obj.properties for obj in response.objects]
    
    def close(self):
        if self.client:
            self.client.close()