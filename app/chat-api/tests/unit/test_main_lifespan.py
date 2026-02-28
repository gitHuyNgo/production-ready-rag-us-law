import pytest

from src.api import main as main_module


class _FakeDB:
    def __init__(self) -> None:
        self.connected = False
        self.closed = False
        self.client = None  

    def connect(self):
        self.connected = True
        self.client = True  
        return self

    def close(self):
        self.closed = True
        self.client = None


class _FakeLLM:
    pass


class _FakeReranker:
    def __init__(self, top_k: int) -> None:
        self.top_k = top_k


@pytest.mark.asyncio
async def test_lifespan_initializes_and_cleans_up(monkeypatch: pytest.MonkeyPatch):
    fake_db = _FakeDB()

    # Ensure startup doesn't fail fast due to missing env in unit tests.
    monkeypatch.setattr(main_module.settings, "OPENAI_API_KEY", "test-key", raising=False)

    # Patch constructors used inside lifespan.
    monkeypatch.setattr(main_module, "WeaviateClient", lambda *args, **kwargs: fake_db)
    monkeypatch.setattr(main_module, "OpenAILLM", lambda *args, **kwargs: _FakeLLM())
    monkeypatch.setattr(main_module, "BM25Reranker", lambda top_k: _FakeReranker(top_k))
    monkeypatch.setattr(main_module, "CohereReranker", lambda top_k: _FakeReranker(top_k))
    fake_cache = type("_FakeCache", (), {"enabled": False, "close": lambda self: None})()
    monkeypatch.setattr(main_module, "SemanticCache", lambda *args, **kwargs: fake_cache)

    app = main_module.app
    # Clear state so lifespan runs real init (other tests' test_client may have set app.state).
    app.state.db = None
    app.state.llm = None

    async with app.router.lifespan_context(app):
        # Inside lifespan: resources should be initialized and attached to state.
        assert app.state.db is fake_db
        assert isinstance(app.state.llm, _FakeLLM)
        assert isinstance(app.state.first_reranker, _FakeReranker)
        assert isinstance(app.state.second_reranker, _FakeReranker)
        assert hasattr(app.state, "semantic_cache")
        assert hasattr(app.state, "embed_model")
        assert fake_db.connected is True

    # After lifespan exits, db.close should have been called.
    assert fake_db.closed is True

