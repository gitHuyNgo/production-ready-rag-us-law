import os
import logging
from pathlib import Path
from code_shared.graph_store.neo4j_client import neo4j_manager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_BATCH_SIZE = 1000

class USCodeGraphIngestor:
    """
    Handles the high-speed structural ingestion of US Code nodes and edges
    into Neo4j using optimized Cypher queries.
    """
    def __init__(self, node_csv_path: str, edge_csv_path: str):
        self.node_csv = Path(node_csv_path).resolve()
        self.edge_csv = Path(edge_csv_path).resolve()
        self.store = neo4j_manager.get_graph_store()
        self.driver = self.store._driver

    def _execute_query(self, query: str, description: str):
        """Helper to execute Cypher queries with logging."""
        try:
            with self.driver.session() as session:
                logger.info(f"Executing: {description}...")
                result = session.run(query)
                summary = result.consume()
                logger.info(f"Finished {description}. Counters: {summary.counters}")
        except Exception as e:
            logger.error(f"Error during {description}: {str(e)}")
            raise

    def create_constraints(self):
        """Ensures data integrity and lookup speed via constraints."""
        query = "CREATE CONSTRAINT section_id_unique IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE"
        self._execute_query(query, "Creating unique constraint for Section ID")

    def load_nodes(self):
        """
        Loads nodes in batches to prevent MemoryPoolOutOfMemoryError.
        Optimized for large content fields in legal documents.
        """
        csv_url = f"file:///{str(self.node_csv).replace('\\', '/')}"
        batch_size = int(os.getenv("BATCH_SIZE", DEFAULT_BATCH_SIZE))
        
        query = f"""
        LOAD CSV WITH HEADERS FROM '{csv_url}' AS row
        CALL {{
            WITH row
            MERGE (s:Section {{id: row.id}})
            SET s.title = row.title,
                s.content = row.content,
                s.title_num = row.title_num,
                s.updated_at = datetime()
        }} IN TRANSACTIONS OF {batch_size} ROWS
        """
        self._execute_query(query, f"Batch loading nodes from {self.node_csv.name}")

    def load_edges(self):
        """
        Loads edges in batches. Ensuring structural integrity without RAM spikes.
        """
        csv_url = f"file:///{str(self.edge_csv).replace('\\', '/')}"
        batch_size = int(os.getenv("BATCH_SIZE", DEFAULT_BATCH_SIZE))
        
        query = f"""
        LOAD CSV WITH HEADERS FROM '{csv_url}' AS row
        CALL {{
            WITH row
            MATCH (source:Section {{id: row.source}})
            MERGE (target:Section {{id: row.target}})
            MERGE (source)-[r:REFERENCES]->(target)
            SET r.updated_at = datetime()
        }} IN TRANSACTIONS OF {batch_size} ROWS
        """
        self._execute_query(query, f"Batch loading edges from {self.edge_csv.name}")

    def run_pipeline(self):
        """Orchestrates the full structural ingestion."""
        logger.info("--- Starting US Code Structural Ingestion ---")
        self.create_constraints()
        self.load_nodes()
        self.load_edges()
        logger.info("--- Ingestion Pipeline Finished Successfully ---")

if __name__ == "__main__":
    NODE_DATA = os.getenv("NODE_CSV_PATH", "app/ingestion-worker/src/vector_store/data/all_nodes.csv")
    EDGE_DATA = os.getenv("EDGE_CSV_PATH", "app/ingestion-worker/src/vector_store/data/all_edges.csv")
    
    ingestor = USCodeGraphIngestor(NODE_DATA, EDGE_DATA)
    ingestor.run_pipeline()