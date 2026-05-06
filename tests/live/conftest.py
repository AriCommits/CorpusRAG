"""Shared fixtures for live integration tests.

These tests require running ChromaDB and Ollama services.
Run with: pytest -m live
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def live_config():
    """Load the real configs/base.yaml."""
    from config.loader import load_config

    config_path = Path("configs/base.yaml")
    if not config_path.exists():
        pytest.skip("configs/base.yaml not found")
    try:
        return load_config(config_path)
    except Exception as e:
        pytest.skip(f"Cannot load config: {e}")


@pytest.fixture(scope="session")
def live_db(live_config):
    """Connect to the real ChromaDB instance."""
    import httpx

    host = live_config.database.host
    port = live_config.database.port
    try:
        r = httpx.get(f"http://{host}:{port}/api/v2/heartbeat", timeout=3)
        if r.status_code != 200:
            pytest.skip(f"ChromaDB not healthy: {r.status_code}")
    except Exception:
        pytest.skip(f"ChromaDB not reachable at {host}:{port}")

    from db import ChromaDBBackend

    return ChromaDBBackend(live_config.database)


@pytest.fixture(scope="session")
def ollama_available(live_config):
    """Check Ollama is reachable, return tags response."""
    import httpx

    endpoint = live_config.llm.endpoint
    try:
        r = httpx.get(f"{endpoint}/api/tags", timeout=5)
        if r.status_code != 200:
            pytest.skip("Ollama not healthy")
        return r.json()
    except Exception:
        pytest.skip(f"Ollama not reachable at {endpoint}")
