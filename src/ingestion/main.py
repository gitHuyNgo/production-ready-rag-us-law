"""
Ingestion script entrypoint: load PDFs from data folder into vector store.
"""
import argparse
from pathlib import Path

from src.core.db_client import WeaviateClient
from src.core.semantic_cache import SemanticCache
from src.ingestion.ingest import IngestionProcessor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DATA_FOLDER = "./data"


def main() -> None:
    """Run ingestion pipeline: connect to DB, process PDFs, close connection."""
    parser = argparse.ArgumentParser(description="Ingest PDFs into the vector store.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete existing collection and create a new one (use when changing embedding dimension, e.g. to 3072).",
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

        # Flush semantic cache so new/updated docs are reflected in answers
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
