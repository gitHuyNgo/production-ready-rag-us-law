"""
Ingestion pipeline: load PDFs, chunk, and index into vector store.
"""
from pathlib import Path
from typing import List

from src.core.base_db import BaseVectorStore
from src.ingestion.chunker import LegalChunker


class IngestionProcessor:
    """Processes PDF files and loads chunks into a vector store."""

    def __init__(self, vector_store: BaseVectorStore) -> None:
        self.db = vector_store
        self.chunker = LegalChunker()

    def run(self, data_path: str) -> None:
        """
        Process all PDFs in the given folder and load chunks into the vector store.

        Args:
            data_path: Path to folder containing PDF files.
        """
        path = Path(data_path)
        files = list(path.glob("*.pdf"))

        if not files:
            print(f"No PDF files found in {data_path}")
            return

        for file in files:
            nodes = self.chunker.load_and_chunk(file)

            chunks_to_load: List[dict] = []
            for node in nodes:
                chunks_to_load.append({
                    "text": node.get_content(),
                    "source": file.name,
                })

            self.db.batch_load(chunks_to_load)
            print(f"Successfully indexed {len(chunks_to_load)} chunks from {file.name}")
