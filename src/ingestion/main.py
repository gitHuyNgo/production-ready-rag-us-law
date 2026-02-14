from src.core.db_client import WeaviateClient
from src.ingestion.ingest import IngestionProcessor


def main():
    db = WeaviateClient()

    try:
        db.connect()
        processor = IngestionProcessor(vector_store=db)
        
        data_folder = "./data"
        processor.run(data_folder)
        
    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()