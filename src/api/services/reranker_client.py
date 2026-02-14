import os
import cohere
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from src.core.config import settings
from .base_reranker import BaseReranker


class BM25Reranker(BaseReranker):
    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not docs:
            return []
            
        corpus = [d.get("text", "") for d in docs]
        tokenized_corpus = [doc.split() for doc in corpus]
        
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)
        
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:self.top_k]]


class CohereReranker(BaseReranker):
    def __init__(self, model: str = "rerank-english-v3.0", top_k: int = 3):
        self.api_key = settings.COHERE_API_KEY
        if not self.api_key:
            raise ValueError("Cohere API Key not found. Set COHERE_API_KEY env var.")
            
        self.client = cohere.ClientV2(self.api_key)
        self.model = model
        self.top_k = top_k

    def rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not docs:
            return []

        doc_texts = [d.get("text", "") for d in docs]

        response = self.client.rerank(
            model=self.model,
            query=query,
            documents=doc_texts,
            top_n=self.top_k,
        )

        final_docs = []
        for result in response.results:
            original_doc = docs[result.index]
            original_doc["rerank_score"] = result.relevance_score
            final_docs.append(original_doc)

        return final_docs