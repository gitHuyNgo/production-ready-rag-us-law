from FlagEmbedding import FlagReranker
from typing import List


class RerankerClient:
    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        self.reranker = FlagReranker(model_name, use_fp16=True)

    def reranking(self, query: str, docs: List[str], top_k: int = None) -> List[dict]:
        pairs = [[query, docs] for doc in docs]
        scores = self.reranker.compute_score(pairs, normalize=True)

        scored_docs = list(zip(scores, docs))
        return sorted(scored_docs, reverse=True)[:top_k]