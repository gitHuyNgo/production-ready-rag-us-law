from typing import Any, Dict, List

import pytest

from src.core.db_client import WeaviateClient
from src.core.config import settings


class _FakeWeaviateCollection:
    def __init__(self) -> None:
        self.deleted: List[str] = []
        self.used_class_names: List[str] = []
        self.created_class_names: List[str] = []
        self.batched_objects: List[Dict[str, Any]] = []
        # In real client, `batch` and `query` are attributes that expose
        # further methods (dynamic, near_vector), so we model that by
        # pointing them at self.
        self.batch = self
        self.query = self

    def delete(self, class_name: str) -> None:
        self.deleted.append(class_name)
        if class_name in self.used_class_names:
            self.used_class_names.remove(class_name)
        if class_name in self.created_class_names:
            self.created_class_names.remove(class_name)

    def exists(self, class_name: str) -> bool:
        return class_name in self.used_class_names or class_name in self.created_class_names

    def create(self, name: str, **kwargs) -> None:
        """Fake create for init_schema (name, properties, vector_config)."""
        self.created_class_names.append(name)

    def use(self, class_name: str):
        self.used_class_names.append(class_name)
        return self

    def near_vector(self, near_vector, limit: int, return_metadata=None):
        class _Resp:
            def __init__(self, items: list[Dict[str, Any]]) -> None:
                self.objects = [type("O", (), {"properties": it}) for it in items]

        # Echo back a single object so that retrieve can unwrap it.
        return _Resp([{"text": "dummy", "source": "test.pdf"}])

    def dynamic(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_object(self, properties: Dict[str, Any], vector: List[float]):
        item = dict(properties)
        item["vector"] = vector
        self.batched_objects.append(item)


class _FakeWeaviateClient:
    def __init__(self) -> None:
        self.collections = _FakeWeaviateCollection()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeEmbedModel:
    def __init__(self) -> None:
        self.calls: List[str] = []

    def get_text_embedding(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.1, 0.2, 0.3]


@pytest.fixture
def patched_weaviate(monkeypatch: pytest.MonkeyPatch):
    fake_client = _FakeWeaviateClient()
    fake_embed = _FakeEmbedModel()

    # Patch external dependencies inside db_client module.
    monkeypatch.setattr("src.core.db_client.weaviate.connect_to_local", lambda *args, **kwargs: fake_client)
    monkeypatch.setattr("src.core.db_client.OpenAIEmbedding", lambda *args, **kwargs: fake_embed)

    return fake_client, fake_embed


def test_weaviate_client_connect_and_close(patched_weaviate):
    fake_client, _ = patched_weaviate

    client = WeaviateClient()
    returned = client.connect()

    assert returned is fake_client
    assert client.client is fake_client

    client.close()
    assert fake_client.closed is True


def test_weaviate_client_batch_load_and_retrieve(patched_weaviate):
    fake_client, fake_embed = patched_weaviate

    client = WeaviateClient()
    client.connect()

    docs = [{"text": "some law", "source": "law.pdf"}]
    client.batch_load(docs)

    # Embedding model should be called for each item
    assert fake_embed.calls == ["some law"]
    assert fake_client.collections.batched_objects

    results = client.retrieve("query text", top_k=1)

    # Embedding model called for query as well
    assert "query text" in fake_embed.calls
    assert results[0]["text"] == "dummy"


def test_weaviate_client_initialize_schema_is_callable(patched_weaviate):
    fake_client, _ = patched_weaviate

    client = WeaviateClient()
    client.connect()

    client.initialize_schema(recreate=False)
    assert settings.WEAVIATE_CLASS_NAME in fake_client.collections.created_class_names

    # Recreate=True when collection exists: delete then create (covers schema delete branch)
    client.initialize_schema(recreate=True)
    assert settings.WEAVIATE_CLASS_NAME in fake_client.collections.deleted
    assert settings.WEAVIATE_CLASS_NAME in fake_client.collections.created_class_names


def test_weaviate_client_initialize_schema_raises_without_connect(patched_weaviate):
    _, _ = patched_weaviate

    client = WeaviateClient()
    # Do not call connect(); client.client is None

    with pytest.raises(RuntimeError, match="Connect before calling initialize_schema"):
        client.initialize_schema(recreate=True)

