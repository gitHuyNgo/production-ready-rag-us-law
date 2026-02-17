"""
Ingestion script entrypoint: load PDFs from data folder into vector store.
"""
from pathlib import Path

from src.core.db_client import WeaviateClient
from src.ingestion.ingest import IngestionProcessor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DATA_FOLDER = "./data"


def main() -> None:
    """Run ingestion pipeline: connect to DB, process PDFs, close connection."""
    db = WeaviateClient()

    try:
        db.connect()
        processor = IngestionProcessor(vector_store=db)

        processor.run(str(DEFAULT_DATA_FOLDER))

    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
