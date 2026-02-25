"""
Ingestion script entrypoint: load PDFs from data folder into vector store.
"""
import argparse

from code_shared.core import WeaviateClient, SemanticCache
from ingestion.ingest import IngestionProcessor


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

    db = WeaviateClient()
    try:
        db.connect()
        if args.recreate:
            db.initialize_schema(recreate=True)
            print("Collection recreated (existing data removed).")
        processor = IngestionProcessor(vector_store=db)
        processor.run(str(args.data))
        cache = SemanticCache()
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
