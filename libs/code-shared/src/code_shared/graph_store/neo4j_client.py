import os
import logging
from typing import Optional
from dotenv import load_dotenv
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

logger = logging.getLogger(__name__)

DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USERNAME = "neo4j"
DEFAULT_NEO4J_DATABASE = "neo4j"
HEALTH_CHECK_QUERY = "MATCH (n) RETURN count(n) as node_count"

class Neo4jClientManager:
    """
    Singleton Manager for Neo4j connections to be shared across microservices.
    Ensures connection pooling and consistent database access.
    """
    _instance: Optional['Neo4jClientManager'] = None
    _graph_store: Optional[Neo4jPropertyGraphStore] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jClientManager, cls).__new__(cls)
            load_dotenv()
        return cls._instance

    def get_graph_store(self) -> Neo4jPropertyGraphStore:
        """
        Initializes and returns the Neo4jPropertyGraphStore instance.
        Uses Bolt protocol as seen in the system configuration.
        """
        if self._graph_store is None:
            uri = os.getenv("NEO4J_URI", DEFAULT_NEO4J_URI)
            username = os.getenv("NEO4J_USERNAME", DEFAULT_NEO4J_USERNAME)
            password = os.getenv("NEO4J_PASSWORD")
            database = os.getenv("NEO4J_DATABASE", DEFAULT_NEO4J_DATABASE)

            if not password:
                logger.error("NEO4J_PASSWORD is not set in environment variables.")
                raise ValueError("Neo4j password must be provided via environment variables.")

            try:
                self._graph_store = Neo4jPropertyGraphStore(
                    username=username,
                    password=password,
                    url=uri,
                    database=database
                )
                logger.info(f"Successfully connected to Neo4j database: {database}")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j connection: {str(e)}")
                raise

        return self._graph_store

    def check_health(self) -> bool:
        """
        Verifies if the database is reachable and contains data.
        Useful for service startup health checks.
        """
        store = self.get_graph_store()
        try:
            with store._driver.session() as session:
                result = session.run(HEALTH_CHECK_QUERY)
                count = result.single()["node_count"]
                logger.info(f"Health Check Passed. Current Nodes: {count}")
                return True
        except Exception as e:
            logger.error(f"Health Check Failed: {str(e)}")
            return False


neo4j_manager = Neo4jClientManager()