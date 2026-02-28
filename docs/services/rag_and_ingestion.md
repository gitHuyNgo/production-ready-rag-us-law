# RAG and Ingestion Architecture

## 1. Overview

The system provides a **Retrieval-Augmented Generation (RAG)** pipeline for US law–oriented Q&A. Legal documents (e.g. PDFs) are ingested into a vector store; at query time the pipeline retrieves relevant chunks, reranks them, builds context, and generates an answer via an LLM. A semantic cache (Redis) can short-circuit repeated or similar queries.

## 2. Components

- **Ingestion worker** (`app/ingestion-worker`): CLI that loads PDFs from a data folder, chunks them (e.g. via Docling + legal chunker), embeds chunks with OpenAI, and batch-writes to Weaviate. After a successful run it flushes the RAG semantic cache so new content is not masked by old cached answers.
- **Chat API** (`app/chat-api`): Owns the Weaviate client for **retrieval**, the Redis semantic cache (get/set), BM25 and Cohere rerankers, and the LLM (OpenAI). Runs the RAG pipeline on each query (or returns a cache hit when applicable).
- **Vector store**: Weaviate; same instance is written by the ingestion worker and read by chat-api. Class name and schema are aligned (e.g. `text`, `source`, self-provided vectors).
- **Semantic cache**: Redis (RediSearch) with a vector index; key prefix and embed dimension are shared so ingestion-worker’s flush clears chat-api’s cache.

## 3. RAG Pipeline (Chat API)

1. **Optional cache**: Compute query embedding; if Redis semantic cache is enabled and a similar cached query exists above threshold, return cached response.
2. **Retrieve**: Query Weaviate for top-k chunks by vector similarity (and any filters).
3. **Rerank**: First reranker (e.g. BM25) then second (e.g. Cohere) to reduce to final top-k.
4. **Context**: Build a formatted string from chunk text and source.
5. **Generate**: Call LLM with system prompt, context, and user query; support streaming.
6. **Chat memory**: If session id is provided, append user message and assistant response to the chat memory store.

Pipeline implementation: `app/chat-api/src/api/services/rag_pipeline.py`; dependencies (db, llm, rerankers, semantic_cache, embed_model) are provided from app state set in lifespan.

## 4. Ingestion Flow

1. Run ingestion worker with `--data <folder>` (and optional `--recreate` to drop and recreate the Weaviate collection).
2. Worker discovers PDFs, converts with Docling, chunks with `LegalChunker`, embeds with OpenAI, and batch-loads into Weaviate.
3. Worker instantiates `SemanticCache` (flush-only) and calls `flush()` so Redis RAG cache is cleared.
4. Subsequent chat queries use the updated Weaviate index and no stale cache.

## 5. Ownership (ADR 003)

- **Chat API**: Full Weaviate client (read/write for RAG) and full Redis semantic cache (get/set, index).
- **Ingestion worker**: Own Weaviate client (write + schema only) and flush-only Redis module; no shared library for Weaviate/Redis so each service manages its own dependencies and config.
