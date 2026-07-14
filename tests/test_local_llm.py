"""
Tests for the offline on-device LLM (M3, llama.cpp).

Skipped where llama_cpp or the GGUF model is absent (e.g. the API backend's
Python); run in the ML venv where both are present.
"""

import importlib.util
from pathlib import Path

import pytest

from src.generation.local_llm import DEFAULT_MODEL_PATH, LocalLLMClient

_HAS_LLAMA = importlib.util.find_spec("llama_cpp") is not None
_HAS_MODEL = Path(DEFAULT_MODEL_PATH).exists()
_READY = _HAS_LLAMA and _HAS_MODEL

pytestmark = pytest.mark.skipif(not _READY, reason="offline LLM not available in this env")


@pytest.fixture(scope="module")
def client():
    return LocalLLMClient(n_ctx=2048)


def test_is_available(client):
    assert client.is_available() is True


def test_empty_prompt_raises(client):
    with pytest.raises(ValueError):
        client.generate("")


def test_generates_grounded_answer(client):
    ctx = (
        "Scheme: PM-KISAN. Eligibility: Small and marginal farmers owning up to "
        "2 hectares. Benefits: Rs 6000 per year in three equal installments."
    )
    q = f"Context:\n{ctx}\n\nQuestion: How much money does PM-KISAN give per year?"
    r = client.generate(q, system_prompt="Answer only from the context.", max_tokens=120)
    assert r["success"] is True
    assert r["response"]
    # The grounded fact must appear in the answer.
    assert "6000" in r["response"] or "6,000" in r["response"]
    assert r["metadata"]["offline"] is True
    assert r["metadata"]["backend"] == "llama.cpp"


def test_metadata_reports_latency_and_tokens(client):
    r = client.generate("Say 'hello' in one word.", max_tokens=10)
    assert r["success"] is True
    assert r["metadata"]["latency_s"] > 0
    assert r["metadata"]["completion_tokens"] is not None
