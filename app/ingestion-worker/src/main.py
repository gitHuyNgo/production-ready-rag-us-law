"""
Ingestion script entrypoint: load PDFs from data folder into vector store.
"""
import argparse

from code_shared.core.db_client import WeaviateClient
from code_shared.core.semantic_cache import SemanticCache
from src.core.config import settings
from src.ingest import IngestionProcessor


DEFAULT_DATA_FOLDER = "./data"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PDFs into the vector store.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete existing collection and create a new one (e.g. when changing embedding dimension).",
    )
    parser.add_argument(
        "--data",
        default=DEFAULT_DATA_FOLDER,
        help=f"Path to folder containing PDFs (default: {DEFAULT_DATA_FOLDER}).",
    )
    args = parser.parse_args()

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required to run ingestion-worker")

    db = WeaviateClient(
        weaviate_url=settings.WEAVIATE_URL,
        weaviate_class_name=settings.WEAVIATE_CLASS_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_embedding_model=settings.OPENAI_EMBEDDING_MODEL,
    )
    try:
        db.connect()
        if args.recreate:
            db.initialize_schema(recreate=True)
            print("Collection recreated (existing data removed).")
        processor = IngestionProcessor(vector_store=db)
        processor.run(str(args.data))
        cache = SemanticCache(
            redis_url=settings.REDIS_URL,
            ttl_seconds=settings.CACHE_TTL_SECONDS,
            similarity_threshold=settings.CACHE_SIMILARITY_THRESHOLD,
            embed_dim=settings.CACHE_EMBED_DIM,
        )
        if cache.enabled:
            cache.flush()
            cache.close()
            print("Semantic cache flushed.")
    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
