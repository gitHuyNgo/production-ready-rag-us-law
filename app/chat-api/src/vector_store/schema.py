"""Weaviate collection schema. Caller passes class_name (from chat-api config)."""
from weaviate.classes.config import Configure, DataType, Property


def init_schema(client, class_name: str, recreate: bool = False) -> None:
    """Create or recreate the document chunk embedding collection."""
    if client.collections.exists(class_name):
        client.collections.delete(class_name)

    client.collections.create(
        name=class_name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
        ],
        vector_config=Configure.Vectors.self_provided(),
    )
