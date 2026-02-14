from typing import List, Dict, Any
from src.core.base_db import BaseVectorStore
from src.core.base_llm import BaseLLM
from .base_reranker import BaseReranker


def transform(docs: List[Dict[str, Any]]) -> str:
    context = []
    for i, d in enumerate(docs, 1):
        part = f"[Chunk {i}]\nSource: {d.get('source', 'Unknown')}\nContent:\n{d.get('text', '')}"
        context.append(part.strip())
    return "\n\n".join(context)

def answer(
    db: BaseVectorStore, 
    llm: BaseLLM, 
    first_reranker: BaseReranker, 
    second_reranker: BaseReranker, 
    query: str
):
    vec_docs = db.retrieve(query, top_k=25)
    
    # filtered_docs = first_reranker.rerank(query, vec_docs)
    
    # final_docs = second_reranker.rerank(query, filtered_docs)

    context = transform(vec_docs)
    return llm.generate(query, context)