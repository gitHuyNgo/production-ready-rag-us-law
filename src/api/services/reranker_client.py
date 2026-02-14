from typing import List
from rank_bm25 import BM25Okapi
from FlagEmbedding import FlagReranker

RERANK_MODEL = "BAAI/bge-reranker-large"


def bm25_rerank(query: str, docs: List[dict], top_k: int = 5):
    corpus = [d["text"] for d in docs]
    tokenized = [doc.split() for doc in corpus]

    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.split())

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_k]]

def bge_rerank(query: str, docs: List[dict], top_k: int = 3):
    reranker = FlagReranker(RERANK_MODEL, use_fp16=True)
    pairs = [(query, d["text"]) for d in docs]
    scores = reranker.compute_score(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_k]]
