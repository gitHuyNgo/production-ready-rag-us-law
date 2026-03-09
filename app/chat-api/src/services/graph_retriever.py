import logging
from typing import List
from llama_index.core.schema import NodeWithScore, TextNode
from code_shared.graph_store.neo4j_client import neo4j_manager

logger = logging.getLogger(__name__)

class LegalGraphRetriever:
    def __init__(self, index):
        self.index = index
        self.graph_store = neo4j_manager.get_graph_store()
        self.driver = self.graph_store._driver

    def retrieve(self, query: str, analysis) -> List[NodeWithScore]:
        candidates = []
        
        if "person" in query.lower() or "definition" in query.lower():
            candidates.extend(self._direct_fetch("/us/usc/t1/s1"))

        vector_nodes = self.index.as_retriever(similarity_top_k=5).retrieve(query)
        candidates.extend(vector_nodes)

        return self._simple_expand(candidates)

    def _direct_fetch(self, section_id: str) -> List[NodeWithScore]:
        nodes = []
        with self.driver.session() as session:
            res = session.run("MATCH (s:Section {id: $id}) RETURN s", id=section_id)
            record = res.single()
            if record:
                n = record['s']
                node = TextNode(text=n['content'], id_=n['id'], metadata={"title": n['title']})
                nodes.append(NodeWithScore(node=node, score=1.0))
        return nodes

    def _simple_expand(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        results = list(nodes)
        if not nodes: return []
        
        with self.driver.session() as session:
            root_id = nodes[0].node.node_id
            query = "MATCH (s:Section {id: $id})-[:REFERENCES]->(neighbor:Section) RETURN neighbor LIMIT 3"
            res = session.run(query, id=root_id)
            for rec in res:
                nb = rec['neighbor']
                node = TextNode(text=nb['content'], id_=nb['id'], metadata={"title": nb['title']})
                results.append(NodeWithScore(node=node, score=0.8))
        return results