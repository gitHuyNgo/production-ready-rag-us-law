from .retriever import vector_retrieve
from .reranker_client import bm25_rerank, bge_rerank
from .llm_client import ask_llm


def transform(docs):
    context = []
    for i, d in enumerate(docs, 1):
        part = f"""
        [Chunk {i}]
        Source: {d['source']}
        Content:
        {d['text']}
        """
        context.append(part.strip())
    return "\n\n".join(context)

def answer(client, llm, query: str):
    vec_docs = vector_retrieve(client, query)
    bm25_docs = bm25_rerank(query, vec_docs)
    final_docs = bge_rerank(query, bm25_docs)

    context = transform(final_docs)
    return ask_llm(llm, query, context)
