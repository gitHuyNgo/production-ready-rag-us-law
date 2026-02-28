"""
Shared code for microservices.

Keep this package `__init__` lightweight: do not import optional/heavy deps at
import time. Import from submodules directly, e.g.:

- `from code_shared.core.exceptions import AppError`
- `from code_shared.core.db_client import WeaviateClient`
- `from code_shared.llm.openai_llm import OpenAILLM`
"""

__all__: list[str] = []
