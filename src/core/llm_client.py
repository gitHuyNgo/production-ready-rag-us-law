"""
OpenAI LLM client for RAG response generation.
"""
from pathlib import Path

from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

from src.core.base_llm import BaseLLM
from src.core.config import settings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "llm" / "prompts"
DEFAULT_MODEL = "gpt-5.1"


class OpenAILLM(BaseLLM):
    """OpenAI-based LLM with system and answer-style prompts."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.llm = OpenAI(model=model, api_key=settings.OPENAI_API_KEY)
        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.answer_style = self._load_prompt("answer_style.txt")

    def _load_prompt(self, filename: str) -> str:
        """Load prompt text from file."""
        path = _PROMPTS_DIR / filename
        return path.read_text(encoding="utf-8").strip()

    def generate(self, query: str, context: str) -> str:
        """Generate answer from query and context using system + answer style."""
        user_content = (
            f"QUESTION:\n{query}\n\nCONTEXT:\n{context}\n\n{self.answer_style}"
        )
        messages = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=user_content),
        ]
        resp = self.llm.chat(messages)
        return resp.message.content
