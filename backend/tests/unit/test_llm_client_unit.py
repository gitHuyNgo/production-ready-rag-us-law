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


def _make_fake_openai_with_stream(stream_chunks: list[Any]):
    """Build a fake OpenAI that returns the given stream chunks from stream_chat."""

    class _FakeStream:
        def __init__(self, chunks):
            self._chunks = chunks

        @property
        def response_gen(self):
            return iter(self._chunks)

    class _FakeOpenAIWithStream(_FakeOpenAI):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._stream_chunks = stream_chunks

        def stream_chat(self, messages):
            return _FakeStream(self._stream_chunks)

    return _FakeOpenAIWithStream


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


def test_openai_llm_stream_chunk_to_str_delta_string(patch_openai_and_prompts, monkeypatch):
    """_stream_chunk_to_str returns chunk.delta when it is a string."""
    chunk = type("C", (), {"delta": "tok1"})()
    FakeOpenAI = _make_fake_openai_with_stream([chunk])
    monkeypatch.setattr(llm_module, "OpenAI", FakeOpenAI)
    llm = OpenAILLM(model="fake")
    out = list(llm.generate_stream("q", "ctx"))
    assert out == ["tok1"]


def test_openai_llm_stream_chunk_to_str_message_content(patch_openai_and_prompts, monkeypatch):
    """_stream_chunk_to_str uses chunk.message.content when delta is missing."""
    chunk = type("C", (), {"message": type("M", (), {"content": "msg"})()})()
    FakeOpenAI = _make_fake_openai_with_stream([chunk])
    monkeypatch.setattr(llm_module, "OpenAI", FakeOpenAI)
    llm = OpenAILLM(model="fake")
    out = list(llm.generate_stream("q", "ctx"))
    assert out == ["msg"]


def test_openai_llm_stream_chunk_to_str_fallback(patch_openai_and_prompts, monkeypatch):
    """_stream_chunk_to_str falls back to str(chunk) when no delta/message."""
    chunk = type("C", (), {})()
    FakeOpenAI = _make_fake_openai_with_stream([chunk])
    monkeypatch.setattr(llm_module, "OpenAI", FakeOpenAI)
    llm = OpenAILLM(model="fake")
    out = list(llm.generate_stream("q", "ctx"))
    assert len(out) == 1
    assert "C" in out[0] or "object" in out[0].lower()


def test_openai_llm_generate_stream_skips_empty_strings(patch_openai_and_prompts, monkeypatch):
    """Empty strings from _stream_chunk_to_str are not yielded."""
    chunk_empty = type("C", (), {"delta": ""})()
    chunk_ok = type("C", (), {"delta": "x"})()
    FakeOpenAI = _make_fake_openai_with_stream([chunk_empty, chunk_ok, chunk_empty])
    monkeypatch.setattr(llm_module, "OpenAI", FakeOpenAI)
    llm = OpenAILLM(model="fake")
    out = list(llm.generate_stream("q", "ctx"))
    assert out == ["x"]

