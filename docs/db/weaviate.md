# Weaviate Vector Store

**Owners**: chat-api (read + write for RAG), ingestion-worker (write + schema only)

**Purpose**: Store document chunk embeddings for semantic search in the RAG pipeline.

## Chat API

- **Location**: `app/chat-api/src/vector_store/` (WeaviateClient, schema, base interface).
- **Usage**: Connects to Weaviate, retrieves top-k chunks by query embedding, and optionally uses the same client’s embed model for queries. Used by the RAG pipeline in `api/services/rag_pipeline.py`.
- **Schema**: Collection has properties (e.g. `text`, `source`) and self-provided vectors (embeddings from OpenAI). Class name is configurable (e.g. `WEAVIATE_CLASS_NAME`).

## Ingestion Worker

- **Location**: `app/ingestion-worker/src/vector_store/` (own WeaviateClient, schema, no retrieve).
- **Usage**: Connects to Weaviate, creates/recreates collection schema, and batch-loads chunk embeddings. After a successful ingest run, it flushes the RAG semantic cache (Redis) so chat-api does not serve stale cached answers.
- **Schema**: Same logical schema (text, source, vectors); schema init can delete and recreate the collection when `--recreate` is used.

## Deployment

- Typically run as a container (e.g. Weaviate image in Docker Compose) on a dedicated port (e.g. 8081 on host, 8080 inside). Both chat-api and ingestion-worker point at the same Weaviate URL in production so ingested data is queried by chat-api.
