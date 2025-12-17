from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional



@dataclass
class PromptAssets:
    system_prompt: str
    answer_style: str


class PromptBuilder:
    def __init__(self, prompt_dir: str = "llm/prompts"):
        self.prompt_dir = prompt_dir

    def _read_text(self, filename: str) -> str:
        path = self.prompt_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()
    
    def load_assets(self) -> PromptAssets:
        return PromptAssets(
            system_prompt=self._read_text("system_prompt.txt"),
            answer_style=self._read_text("answer_style.txt")
        )
    
    @staticmethod
    def build_context_from_docs(docs: List[Dict[str, Any]], max_chars: Optional[int] = None) -> str:
        parts: List[str] = []
        total = 0

        for i, d in enumerate(docs, start=1):
            content = (d.get("content") or "").strip()
            if not content:
                continue
                
            meta = d.get("metadata") or {}
            source = meta.get("source")
            page = meta.get("page")
            header_bits = [f"[Doc {i}]"]
            if source:
                header_bits.append(f"source={source}")
            if page is not None:
                header_bits.append(f"page={page}")
            header = " ".join(header_bits)

            chunk = f"{header}\n{content}"
            if max_chars is not None and total + len(chunk) > max_chars:
                remaining = max_chars - total
                if remaining <= 0:
                    break
                chunk = chunk[:remaining]
            parts.append(chunk)
            total += len(chunk)
            if max_chars is not None and total >= max_chars:
                break
        
        return "\n\n".join(parts).strip()

    def build_prompt(self, user_query: str, context: str) -> str:
        assets = self.load_assets()

        prompt = f"""
        {assets.system_prompt}

        === CONTEXT (U.S. Code excerpts) ===
        {context}

        === USER QUESTION ===
        {user_query}

        === ANSWER STYLE ===
        {assets.answer_style}
        """.strip()

        return prompt