import os
import weaviate
from weaviate.classes.query import MetadataQuery
from llama_index.embeddings.openai import OpenAIEmbedding

CLASS_NAME = "document_chunk_embedding"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def connect_weaviate():
    return weaviate.connect_to_local()

def vector_retrieve(client, query: str, top_k: int = 10):
    embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)
    query_vector = embed_model.get_text_embedding(query)

    collection = client.collections.use(CLASS_NAME)
    response = collection.query.near_vector(
        near_vector=query_vector,
        limit=top_k,
        return_metadata=MetadataQuery(distance=True),
    )
    return [obj.properties for obj in response.objects]