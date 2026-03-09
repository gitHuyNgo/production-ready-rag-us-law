import logging
from typing import List
from llama_index.core.schema import NodeWithScore
from code_shared.core.formatter import LegalFormatter

logger = logging.getLogger(__name__)

class LegalContextEngine:
    """
    Ranks retrieved legal nodes and constructs a structured prompt 
    for the LLM, ensuring citations are clearly labeled.
    """
    
    def __init__(self, max_context_tokens: int = 4000):
        # Limit to avoid the 8,192/14,822 token errors you saw earlier
        self.max_context_tokens = max_context_tokens

    def rerank_and_filter(self, nodes: List[NodeWithScore], top_n: int = 5) -> List[NodeWithScore]:
        """
        Groups and ranks nodes. In a more advanced version, 
        you could use a Cross-Encoder (BGE-Reranker) here.
        """
        # Sort by score descending (Vector matches 1.0, Citations 0.8)
        sorted_nodes = sorted(nodes, key=lambda x: x.score, reverse=True)
        
        # Deduplicate by ID just in case
        seen_ids = set()
        unique_nodes = []
        for n in sorted_nodes:
            if n.node.node_id not in seen_ids:
                unique_nodes.append(n)
                seen_ids.add(n.node.node_id)
        
        return unique_nodes[:top_n]

    def build_context_string(self, ranked_nodes: List[NodeWithScore]) -> str:
        """
        Formats legal nodes into a clean string for the LLM.
        Includes Source IDs and Titles for legal accuracy.
        """
        context_parts = []
        
        for i, n in enumerate(ranked_nodes):
            node_id = n.node.metadata.get("source_id") or n.node.node_id
            title = n.node.metadata.get("title", "Unknown Title")
            is_citation = n.node.metadata.get("is_citation", False)
            
            prefix = "[CITED REFERENCE]" if is_citation else "[PRIMARY SOURCE]"
            
            part = (
                f"--- {prefix} {i+1} ---\n"
                f"ID: {node_id}\n"
                f"TITLE: {title}\n"
                f"CONTENT: {n.node.get_content()}\n"
            )
            context_parts.append(part)
        
        return "\n\n".join(context_parts)

    def create_final_prompt(self, query: str, context: str) -> str:
            return f"""
    You are an expert US Law AI Assistant. Your task is to answer the user query using only the provided legal context below.

    CONTEXT FROM LEGAL GRAPH:
    {context}

    USER QUERY: {query}

    STRICT GUIDELINES:
    1. Base your answer ONLY on the provided context.
    2. ALWAYS cite the specific section using the '§' symbol (e.g., 1 U.S.C. § 1). 
    3. DO NOT use raw identifiers like '/us/usc/t1/s1' in your final response.
    4. If the context does not contain the answer, say "I don't have enough information."

    ANSWER:
    """
    
    def build_context_string(self, ranked_nodes: list) -> str:
        context_parts = []
        for i, n in enumerate(ranked_nodes):
            raw_id = n.node.metadata.get("source_id") or n.node.node_id
            # BIẾN ĐỔI TẠI ĐÂY
            friendly_id = LegalFormatter.format_id(raw_id) 
            
            title = n.node.metadata.get("title", "Unknown Title")
            is_citation = n.node.metadata.get("is_citation", False)
            
            prefix = "[CITED REFERENCE]" if is_citation else "[PRIMARY SOURCE]"
            
            part = (
                f"--- {prefix} {i+1} ---\n"
                f"REFERENCE: {friendly_id}\n"
                f"TITLE: {title}\n"
                f"CONTENT: {n.node.get_content()}\n"
            )
            context_parts.append(part)
        return "\n\n".join(context_parts)
    
# Singleton for the service layer
context_engine = LegalContextEngine()