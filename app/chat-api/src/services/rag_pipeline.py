import time
import re
from typing import Dict, Any, List
from llama_index.llms.openai import OpenAI
from llama_index.core import PropertyGraphIndex
from code_shared.graph_store.neo4j_client import neo4j_manager
from services.intent_router import QueryIntent, intent_router
from services.graph_retriever import LegalGraphRetriever

class LegalGrapRAGPipeline:
    def __init__(self):
        self.graph_store = neo4j_manager.get_graph_store()
        self.index = PropertyGraphIndex.from_existing(property_graph_store=self.graph_store)
        self.retriever = LegalGraphRetriever(index=self.index)
        self.llm = OpenAI(model="gpt-4o-mini")

    async def answer(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()
        try:
            analysis = intent_router.route_query(user_query)

            if analysis.intent == QueryIntent.GREETING:
                response = await self.llm.acomplete(
                    f"You are a helpful US Law AI. Respond friendly to: {user_query}"
                )
                return {
                    "answer": str(response),
                    "citations": [],
                    "metadata": {"latency": f"{time.time() - start_time:.2f}s", "type": "chat"}
                }
            
            nodes = self.retriever.retrieve(user_query, analysis)
            
            if not nodes:
                return {"answer": "No data found.", "citations": [], "metadata": {}}

            source_map = {n.node.node_id: n.node.get_content() for n in nodes[:8]}
            
            context_str = "\n\n".join([f"ID: {node_id}\n{content}" for node_id, content in source_map.items()])
            
            prompt = (
                f"You are a legal assistant. Answer ONLY using the context below.\n"
                f"If you use information from a specific ID, you MUST mention that ID in your answer.\n\n"
                f"CONTEXT:\n{context_str}\n\n"
                f"QUERY: {user_query}"
            )
            
            response = await self.llm.acomplete(prompt)
            answer_text = str(response)

            verified_citations = [
                node_id for node_id in source_map.keys() 
                if node_id in answer_text
            ]

            debug_info = {
                cite: source_map[cite][:200] + "..."
                for cite in verified_citations
            }

            return {
                "answer": answer_text,
                "citations": verified_citations,
                "debug_info": debug_info,
                "metadata": {
                    "latency": f"{time.time() - start_time:.2f}s",
                    "total_nodes_retrieved": len(nodes)
                }
            }
        except Exception as e:
            return {
                "answer": f"System Error: {str(e)}", 
                "citations": [], 
                "metadata": {"latency": f"{time.time() - start_time:.2f}s"} 
            }

rag_pipeline = LegalGrapRAGPipeline()