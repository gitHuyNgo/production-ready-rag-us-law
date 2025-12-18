from typing import List
import os

from services.retriever import WeaviateRetriever
from services.reranker_client import RerankerClient

from llm.prompt_builder import PromptBuilder
from llm.factory import create_llm_client


class RAGPipeline:
    def __init__(
        self,
        retriever: WeaviateRetriever,
        reranker: RerankerClient,
        prompt_builder: PromptBuilder,
        llm_client,
        *,
        retrieve_top_k: int = 20,
        rerank_top_k: int = 5,
        max_context_chars: int = 12000,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.prompt_builder = prompt_builder
        self.llm = llm_client

        self.retrieve_top_k = retrieve_top_k
        self.rerank_top_k = rerank_top_k
        self.max_context_chars = max_context_chars
    
    def answer(self, query: str) -> str:
        query_embedding = self.retriever.embed_query(query)

        docs = self.retriever.retrieve(
            query_embedding=query_embedding,
            top_k=self.retrieve_top_k
        )

        if not docs:
            return "The provided U.S. Code text does not contain information relevant to this question."
        
        docs = self.reranker.reranking(
            query=query,
            docs=docs,
            top_k=self.rerank_top_k
        )

        context = self.prompt_builder.build_context_from_docs(
            docs,
            max_chars=self.max_context_chars
        )

        prompt = self.prompt_builder.build_prompt(
            user_query=query,
            context=context
        )

        answer = self.llm.generate(prompt)

        return answer.strip()