"""
Weaviate collection schema definition.
"""
from weaviate.classes.config import Configure, DataType, Property

from code_shared.core.config import settings


def init_schema(client, recreate: bool = False) -> None:
    """
    Create or recreate the document chunk embedding collection.
    """
    if client.collections.exists(settings.WEAVIATE_CLASS_NAME):
        client.collections.delete(settings.WEAVIATE_CLASS_NAME)

    client.collections.create(
        name=settings.WEAVIATE_CLASS_NAME,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
        ],
        vector_config=Configure.Vectors.self_provided(),
    )
