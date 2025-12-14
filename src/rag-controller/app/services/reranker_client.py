from typing import List
from FlagEmbedding import FlagReranker
from rank_bm25 import BM25Okapi

class RerankerClient:
    def __init__(self, model_name: str = "BAAI/bge-reranker-large", alpha: float = 0.5):
        self.reranker = FlagReranker(model_name, use_fp16=True)
        self.alpha = alpha

    def reranking(self, query: str, docs: List[str], top_k: int = None) -> List[dict]:
        if not docs:
            return docs

        tokenized_docs = [
            doc["content"].split()
            for doc in docs
        ]
        bm25 = BM25Okapi(tokenized_docs)
        bm25_scores = bm25.get_scores(query.split())

        pairs = [
            [query, doc["content"]]
            for doc in docs
        ]
        semantic_scores = self.reranker.compute_score(
            pairs,
            normalize=True
        )

        for doc, bm25_s, sem_s in zip(docs, bm25_scores, semantic_scores):
            doc["bm25_score"] = float(bm25_s)
            doc["semantic_scores"] = float(sem_s)
            doc["hybrid_score"] = (
                self.alpha * doc["semantic_scores"]
                + (1 - self.alpha) * doc["bm25_score"]
            )
        
        doc = sorted(docs, key=lambda d: d["hybrid_score"], reverse=True)

        if top_k is not None:
            docs = docs[:top_k]
        
        return docs