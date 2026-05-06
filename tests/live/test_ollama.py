"""Live tests for Ollama connectivity."""

import pytest

pytestmark = pytest.mark.live


def test_ollama_reachable(live_config):
    import httpx

    try:
        r = httpx.get(f"{live_config.llm.endpoint}/api/tags", timeout=5)
    except httpx.ConnectError:
        pytest.skip(f"Ollama not reachable at {live_config.llm.endpoint}")
    assert r.status_code == 200


def test_configured_model_available(live_config, ollama_available):
    models = [m["name"].split(":")[0] for m in ollama_available.get("models", [])]
    model_name = live_config.llm.model.split(":")[0]
    assert model_name in models, f"{live_config.llm.model} not found. Available: {models}"


def test_embedding_model_available(live_config, ollama_available):
    models = [m["name"].split(":")[0] for m in ollama_available.get("models", [])]
    embed_model = live_config.embedding.model.split(":")[0]
    assert embed_model in models, f"{live_config.embedding.model} not found. Available: {models}"


def test_generate_response(live_config, ollama_available):
    import httpx

    r = httpx.post(
        f"{live_config.llm.endpoint}/api/generate",
        json={"model": live_config.llm.model, "prompt": "Say hello.", "stream": False},
        timeout=60,
    )
    assert r.status_code == 200
    assert len(r.json().get("response", "")) > 0


def test_embed_text(live_config, ollama_available):
    import httpx

    r = httpx.post(
        f"{live_config.llm.endpoint}/api/embed",
        json={"model": live_config.embedding.model, "input": "test embedding"},
        timeout=30,
    )
    assert r.status_code == 200
    embeddings = r.json().get("embeddings", [])
    assert len(embeddings) > 0
    assert len(embeddings[0]) > 100, f"Expected >100 dimensions, got {len(embeddings[0])}"
