from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
from src.core.config import settings
from .base_llm import BaseLLM
from pathlib import Path


class OpenAILLM(BaseLLM):
    def __init__(self, model: str = "gpt-5.1"):
        self.llm = OpenAI(model=model, api_key=settings.OPENAI_API_KEY)
        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.answer_style = self._load_prompt("answer_style.txt")

    def _load_prompt(self, filename: str) -> str:
        path = Path(__file__).resolve().parents[2] / "llm" / "prompts" / filename
        return path.read_text(encoding="utf-8").strip()

    def generate(self, query: str, context: str) -> str:
        user_content = f"QUESTION:\n{query}\n\nCONTEXT:\n{context}\n\n{self.answer_style}"
        messages = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=user_content),
        ]
        resp = self.llm.chat(messages)
        return resp.message.content