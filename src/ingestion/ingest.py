from typing import List
from pathlib import Path
from src.core.base_db import BaseVectorStore
from .chunker import LegalChunker


class IngestionProcessor:
    def __init__(self, vector_store: BaseVectorStore):
        self.db = vector_store
        self.chunker = LegalChunker()

    def run(self, data_path: str):
        path = Path(data_path)
        files = list(path.glob("*.pdf"))
        
        if not files:
            print(f"No PDF files found in {data_path}")
            return

        for file in files:
            nodes = self.chunker.load_and_chunk(file)

            chunks_to_load = []
            for node in nodes:
                chunks_to_load.append({
                    "text": node.get_content(),
                    "source": file.name,
                })
            
            self.db.batch_load(chunks_to_load)
            print(f"Successfully indexed {len(chunks_to_load)} chunks from {file.name}")