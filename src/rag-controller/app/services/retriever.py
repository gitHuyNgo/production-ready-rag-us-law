import weaviate
from typing import List


class WeaviateRetriever:
    def __init__(self, client, collection_name: str):
        self.client = client
        self.collection = client.collections.use(collection_name)

    def retrieve(self, query_embedding: List[float], top_k: int = 5):
        response = self.collection.query.near_vector(
            query=query_embedding,
            limit=top_k,
            return_properties=["content", "source", "page"]
        )

        docs = []
        for obj in response.objects:
            docs.append({
                "content": obj.properties["content"],
                "metadata": {
                    "source": obj.properties.get("source"),
                    "page": obj.properties.get("page"),
                },
            })

        return docs