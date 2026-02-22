import pytest

from src.core.llm_client import OpenAILLM
from src.core.config import settings

@pytest.mark.external
def test_openai_llm_live_call_when_key_present():
    """Smoke test that hits the live OpenAI chat API through OpenAILLM."""
    api_key = settings.OPENAI_API_KEY
    if not api_key or api_key == "dummy":
        pytest.skip("OPENAI_API_KEY not set to a real key")

    llm = OpenAILLM()

    # Use a tiny query/context to minimize token usage and latency.
    answer = llm.generate("Ping?", "Short context.")

    assert isinstance(answer, str)
    assert answer.strip() != ""

