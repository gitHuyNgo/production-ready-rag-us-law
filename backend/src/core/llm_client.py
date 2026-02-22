"""
OpenAI LLM client for RAG response generation.
"""
from pathlib import Path
from typing import Iterator

from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

from src.core.base_llm import BaseLLM
from src.core.config import settings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


class OpenAILLM(BaseLLM):
    """OpenAI-based LLM with system and answer-style prompts."""

    def __init__(self, model: str = settings.OPENAI_LLM_MODEL) -> None:
        self.llm = OpenAI(model=model, api_key=settings.OPENAI_API_KEY)
        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.answer_style = self._load_prompt("answer_style.txt")

    def _load_prompt(self, filename: str) -> str:
        """Load prompt text from file."""
        path = _PROMPTS_DIR / filename
        return path.read_text(encoding="utf-8").strip()

    def _messages(self, query: str, context: str) -> list:
        """Build chat messages for query and context."""
        user_content = (
            f"QUESTION:\n{query}\n\nCONTEXT:\n{context}\n\n{self.answer_style}"
        )
        return [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=user_content),
        ]

    def generate(self, query: str, context: str) -> str:
        """Generate answer from query and context using system + answer style."""
        messages = self._messages(query, context)
        resp = self.llm.chat(messages)
        return resp.message.content

    def _stream_chunk_to_str(self, chunk) -> str:
        """Extract string from stream chunk (ChatResponse or string)."""
        delta = getattr(chunk, "delta", None)
        if delta is not None:
            return delta if isinstance(delta, str) else str(delta)
        msg = getattr(chunk, "message", None)
        if msg is not None:
            content = getattr(msg, "content", None)
            if content is not None:
                return content if isinstance(content, str) else str(content)
        return str(chunk)

    def generate_stream(self, query: str, context: str) -> Iterator[str]:
        """Stream answer tokens from query and context."""
        messages = self._messages(query, context)
        stream = self.llm.stream_chat(messages)
        # Support both: .response_gen (older) or iterator directly (newer)
        gen = getattr(stream, "response_gen", stream)
        for chunk in gen:
            text = self._stream_chunk_to_str(chunk)
            if text:
                yield text
