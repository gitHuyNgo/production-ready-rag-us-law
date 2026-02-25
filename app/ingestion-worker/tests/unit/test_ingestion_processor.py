from pathlib import Path

import pytest

from ingestion.ingest import IngestionProcessor


class _FakeNode:
    def __init__(self, content: str) -> None:
        self._content = content

    def get_content(self) -> str:
        return self._content


class _FakeChunker:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def load_and_chunk(self, file_path: Path):
        self.calls.append(file_path)
        return [_FakeNode("a"), _FakeNode("b")]


class _FakeVectorStore:
    def __init__(self) -> None:
        self.loaded = []

    def batch_load(self, items):
        self.loaded.append(items)


def test_ingestion_processor_no_files(tmp_path: Path):
    db = _FakeVectorStore()
    processor = IngestionProcessor(vector_store=db)
    fake_chunker = _FakeChunker()
    processor.chunker = fake_chunker  # type: ignore[assignment]
    processor.run(str(tmp_path))
    assert fake_chunker.calls == []
    assert db.loaded == []


def test_ingestion_processor_loads_chunks(tmp_path: Path):
    pdf_path = tmp_path / "case.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 dummy content")
    db = _FakeVectorStore()
    processor = IngestionProcessor(vector_store=db)
    fake_chunker = _FakeChunker()
    processor.chunker = fake_chunker  # type: ignore[assignment]
    processor.run(str(tmp_path))
    assert fake_chunker.calls == [pdf_path]
    assert len(db.loaded) == 1
    loaded_batch = db.loaded[0]
    assert len(loaded_batch) == 2
    assert loaded_batch[0]["source"] == "case.pdf"
