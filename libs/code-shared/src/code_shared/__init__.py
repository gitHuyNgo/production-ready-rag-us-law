"""
Shared code for microservices (exceptions, LLM).

Weaviate and Redis/semantic cache live in chat-api; ingestion-worker has its own
vector_store and semantic_cache for write/flush. Import from submodules, e.g.:

- `from code_shared.core.exceptions import AppError`
- `from code_shared.llm import OpenAILLM`
"""

__all__: list[str] = []
