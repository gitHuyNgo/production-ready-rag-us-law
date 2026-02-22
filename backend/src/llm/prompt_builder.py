"""
Prompt building utilities for LLM context and style.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PromptAssets:
    """Loaded prompt text assets."""

    system_prompt: str
    answer_style: str


class PromptBuilder:
    """Build prompts from template files and document context."""

    def __init__(self, prompt_dir: str = "llm/prompts") -> None:
        self.prompt_dir = Path(prompt_dir)

    def _read_text(self, filename: str) -> str:
        """Read and return prompt file contents."""
        path = self.prompt_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    def load_assets(self) -> PromptAssets:
        """Load system prompt and answer style from files."""
        return PromptAssets(
            system_prompt=self._read_text("system_prompt.txt"),
            answer_style=self._read_text("answer_style.txt"),
        )

    @staticmethod
    def build_context_from_docs(
        docs: List[Dict[str, Any]],
        max_chars: Optional[int] = None,
    ) -> str:
        """
        Build formatted context string from documents.

        Args:
            docs: List of dicts with 'content' and 'metadata'.
            max_chars: Optional max total character count.

        Returns:
            Formatted context string.
        """
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
        """Build full prompt with system, context, and answer style."""
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
