from weaviate.classes.config import Property, DataType, Configure

CLASS_NAME = "document_chunk_embedding"


def init_schema(client, recreate: bool = False):
    if client.collections.exists(CLASS_NAME):
        client.collections.delete(CLASS_NAME)

    client.collections.create(
    name=CLASS_NAME,
    properties=[
        Property(name="text", data_type=DataType.TEXT),
        Property(name="source", data_type=DataType.TEXT),
    ],
    vector_config=Configure.Vectors.self_provided(),
    )