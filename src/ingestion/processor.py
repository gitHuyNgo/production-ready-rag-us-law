from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

from retriever import connect_weaviate
from schema import init_schema
from chunk import load_and_chunk
from llama_index.embeddings.openai import OpenAIEmbedding

CLASS_NAME = "document_chunk_embedding"
BASE_FILE = Path(__file__).resolve()
PROJECT_ROOT = BASE_FILE.parents[4]
DATA_PATH = PROJECT_ROOT / "data"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def main():
    client = connect_weaviate()
    embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)

    try:
        init_schema(client, recreate=True)

        collection = client.collections.use(CLASS_NAME)

        for source, nodes in load_and_chunk(DATA_PATH):
            for node in nodes:
                vector = embed_model.get_text_embedding(node.text)
                collection.data.insert(
                    properties={
                        "text": node.text,
                        "source": source,
                    },
                    vector=vector,
                )
    finally:
        client.close()

if __name__ == "__main__":
    main()