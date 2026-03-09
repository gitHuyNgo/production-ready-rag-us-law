import os
import time
import logging
from typing import List
from dotenv import load_dotenv
from llama_index.core import PropertyGraphIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from openai import RateLimitError, BadRequestError

from code_shared.graph_store.neo4j_client import neo4j_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_CHUNK_SIZE = 2048
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_TPM_BATCH_SLEEP = 15
DEFAULT_TPM_LIMIT_SLEEP = 60

class USCodeEmbeddingWorker:
    """
    Background worker that fetches text from Neo4j, generates embeddings 
    using OpenAI, and syncs them back to the graph.
    """
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        load_dotenv()
        
        chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", DEFAULT_CHUNK_SIZE))
        chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP))
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")
        
        embedding_model = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        Settings.embed_model = OpenAIEmbedding(
            model=embedding_model, 
            api_key=api_key
        )
        
        self.text_splitter = SentenceSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        
        self.graph_store = neo4j_manager.get_graph_store()
        self.index = PropertyGraphIndex.from_existing(
            property_graph_store=self.graph_store,
            embed_model=Settings.embed_model
        )

    def _fetch_pending_nodes(self, limit: int):
        """Fetches nodes that have content but no embeddings yet."""
        query = """
        MATCH (s:Section) 
        WHERE s.content IS NOT NULL AND s.embedding IS NULL 
        RETURN s.id as id, s.content as content, s.title as title
        LIMIT $limit
        """
        with self.graph_store._driver.session() as session:
            result = session.run(query, limit=limit)
            return list(result)

    def run_sync(self, total_limit: int = 1000, batch_size: int = 10):
        """
        Main loop to process embeddings in batches to stay under the 30k TPM limit.
        """
        logger.info(f"--- Starting Embedding Sync (Limit: {total_limit}) ---")
        
        tpm_batch_sleep = int(os.getenv("TPM_BATCH_SLEEP", DEFAULT_TPM_BATCH_SLEEP))
        tpm_limit_sleep = int(os.getenv("TPM_LIMIT_SLEEP", DEFAULT_TPM_LIMIT_SLEEP))
        
        pending_records = self._fetch_pending_nodes(total_limit)
        if not pending_records:
            logger.info("No nodes found requiring embeddings. Task complete.")
            return

        for i in range(0, len(pending_records), batch_size):
            batch = pending_records[i : i + batch_size]
            nodes_to_insert = []

            for record in batch:
                chunks = self.text_splitter.split_text(record['content'])
                
                for idx, chunk_text in enumerate(chunks):
                    nodes_to_insert.append(TextNode(
                        text=chunk_text,
                        id_=f"{record['id']}_ch_{idx}",
                        metadata={
                            "source_id": record['id'], 
                            "title": record['title'],
                            "is_chunk": len(chunks) > 1
                        }
                    ))

            try:
                self.index.insert_nodes(nodes_to_insert)
                logger.info(f"Batch {i//batch_size + 1}: Embedded {len(nodes_to_insert)} chunks.")
                
                time.sleep(tpm_batch_sleep) 
                
            except RateLimitError:
                logger.warning(f"TPM Limit reached. Sleeping for {tpm_limit_sleep} seconds...")
                time.sleep(tpm_limit_sleep)
                self.index.insert_nodes(nodes_to_insert)
            except BadRequestError as e:
                logger.error(f"Failed to process nodes due to size/content: {e}")
                continue

        logger.info("--- Embedding Sync Finished ---")

if __name__ == "__main__":
    worker = USCodeEmbeddingWorker()
    worker.run_sync(total_limit=500, batch_size=10)