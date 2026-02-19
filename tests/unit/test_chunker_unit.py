from pathlib import Path

import pytest

from src.ingestion.chunker import LegalChunker


class _FakeDoc:
    def __init__(self, text: str) -> None:
        self._text = text

    def export_to_markdown(self) -> str:
        return self._text


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.document = _FakeDoc(text)


class _FakeConverter:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def convert(self, file_path: Path):
        self.calls.append(file_path)
        return _FakeResult("markdown")


class _FakeParser:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_nodes_from_documents(self, docs):
        # Track that markdown text made it through to the parser.
        self.calls.append(docs[0].text)
        return ["node1", "node2"]


@pytest.fixture
def patch_chunker(monkeypatch: pytest.MonkeyPatch):
    fake_converter = _FakeConverter()
    fake_parser = _FakeParser()

    monkeypatch.setattr("src.ingestion.chunker.DocumentConverter", lambda: fake_converter)
    monkeypatch.setattr("src.ingestion.chunker.MarkdownNodeParser", lambda: fake_parser)

    return fake_converter, fake_parser


def test_legal_chunker_load_and_chunk(patch_chunker, tmp_path: Path):
    fake_converter, fake_parser = patch_chunker

    pdf_path = tmp_path / "case.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 dummy")

    chunker = LegalChunker()
    nodes = chunker.load_and_chunk(pdf_path)

    assert fake_converter.calls == [pdf_path]
    assert fake_parser.calls == ["markdown"]
    assert nodes == ["node1", "node2"]

