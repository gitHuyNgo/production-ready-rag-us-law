from typing import Any
from pathlib import Path

import pytest

from src.core import llm_client as llm_module
from src.core.llm_client import OpenAILLM


class _FakeChatResponse:
    def __init__(self, content: str) -> None:
        self.message = type("M", (), {"content": content})


class _FakeOpenAI:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key
        self.chats: list[dict[str, Any]] = []

    def chat(self, messages):
        self.chats.append({"messages": messages})
        return _FakeChatResponse("unit-test-response")


@pytest.fixture
def patch_openai_and_prompts(monkeypatch: pytest.MonkeyPatch):
    # Patch the OpenAI class used inside the module.
    monkeypatch.setattr(llm_module, "OpenAI", _FakeOpenAI)

    # Avoid touching real prompt files on disk.
    monkeypatch.setattr(
        OpenAILLM,
        "_load_prompt",
        lambda self, filename: f"PROMPT:{filename}",
    )


def test_openai_llm_generate_builds_messages_and_returns_content(patch_openai_and_prompts):
    llm = OpenAILLM(model="fake-model")

    answer = llm.generate("What is law?", "Some context")

    assert answer == "unit-test-response"


def test_openai_llm_load_prompt_reads_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # Patch prompts directory so that _load_prompt reads from a temp location.
    monkeypatch.setattr(llm_module, "_PROMPTS_DIR", tmp_path)

    # Create fake prompt files expected by __init__
    (tmp_path / "system_prompt.txt").write_text("SYSTEM", encoding="utf-8")
    (tmp_path / "answer_style.txt").write_text("STYLE", encoding="utf-8")

    # Patch OpenAI to avoid real API calls, but do NOT patch _load_prompt here.
    monkeypatch.setattr(llm_module, "OpenAI", _FakeOpenAI)

    llm = OpenAILLM(model="fake")

    assert llm.system_prompt == "SYSTEM"
    assert llm.answer_style == "STYLE"

