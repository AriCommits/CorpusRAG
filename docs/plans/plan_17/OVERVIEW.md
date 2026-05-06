# Plan 17: Live Config Integration Tests

## Summary

Add a new test tier (`tests/live/`) that validates CorpusRAG against the user's **actual** `configs/base.yaml` and a **running ChromaDB instance**. These tests catch the class of bugs where unit tests pass (using mocks/persistent mode) but the real CLI fails (wrong port, missing collections, Ollama down, embedding model not pulled, etc.).

## Goals

- Tests that load the real `configs/base.yaml` — not synthetic YAML
- Tests that connect to the actual ChromaDB HTTP server (port 8001)
- Tests that verify Ollama is reachable and the configured model responds
- Tests that verify the embedding model produces vectors of expected dimensions
- A `corpus doctor` CLI command that runs these checks interactively
- Pytest marker `@pytest.mark.live` so these tests are skipped by default and only run explicitly (`pytest -m live`)
- Clear separation: `tests/live/` directory, never runs in CI (requires local infra)

## Non-Goals

- Replacing existing unit/integration tests (those stay as-is)
- Requiring Docker to be running for normal `pytest` runs
- Testing LLM response quality (just connectivity and basic function)

## Background / Context

Current test setup:
- Unit tests use `MagicMock` for config and DB — never touch real services
- Integration tests use `mode: persistent` (in-process ChromaDB) — never test HTTP transport
- The user's actual config uses `mode: http, port: 8001` — a completely different code path

This means tests pass but `corpus rag query "test" -c notes` fails because:
1. ChromaDB HTTP client initialization differs from persistent mode
2. Embedding model might not be pulled in Ollama
3. Collection might not exist
4. Config file might have YAML errors the tests never parse

## Features / Tasks

### T1: Shared Live Fixtures
**Files:** `tests/live/__init__.py` (NEW), `tests/live/conftest.py` (NEW)
**Complexity:** M
**Depends on:** none

Create `tests/live/conftest.py` with fixtures that:
- Load `configs/base.yaml` via `config.loader.load_config()`
- Create a real `ChromaDBBackend` in HTTP mode from the loaded config
- Skip the entire module if ChromaDB is unreachable (`pytest.importorskip` pattern)
- Provide a `live_config` and `live_db` fixture

```python
import pytest
from config.loader import load_config
from config.base import BaseConfig
from db import ChromaDBBackend

def _check_chromadb(config):
    """Return True if ChromaDB is reachable."""
    import httpx
    try:
        r = httpx.get(f"http://{config.database.host}:{config.database.port}/api/v2/heartbeat", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

@pytest.fixture(scope="session")
def live_config():
    try:
        cfg = load_config(Path("configs/base.yaml"))
    except Exception as e:
        pytest.skip(f"Cannot load configs/base.yaml: {e}")
    return cfg

@pytest.fixture(scope="session")
def live_db(live_config):
    if not _check_chromadb(live_config):
        pytest.skip("ChromaDB not reachable")
    return ChromaDBBackend(live_config.database)
```

### T2: ChromaDB Connectivity Tests
**Files:** `tests/live/test_chromadb.py` (NEW)
**Complexity:** S
**Depends on:** T1

Tests:
- `test_chromadb_heartbeat` — HTTP GET to `/api/v2/heartbeat` returns 200
- `test_list_collections` — `live_db.list_collections()` returns a list (may be empty)
- `test_create_and_delete_collection` — create `_test_live_probe`, verify exists, delete
- `test_add_and_query_document` — add a doc with a real embedding, query it back

### T3: Ollama Connectivity Tests
**Files:** `tests/live/test_ollama.py` (NEW)
**Complexity:** S
**Depends on:** T1

Tests:
- `test_ollama_reachable` — GET `/api/tags` returns 200
- `test_configured_model_available` — the model in `live_config.llm.model` is in the tags list
- `test_embedding_model_available` — `live_config.embedding.model` is in the tags list
- `test_generate_response` — POST `/api/generate` with a simple prompt returns text
- `test_embed_text` — POST `/api/embed` returns a vector of expected length

### T4: End-to-End RAG Pipeline Test
**Files:** `tests/live/test_rag_pipeline.py` (NEW)
**Complexity:** M
**Depends on:** T1, T2, T3

Tests:
- `test_ingest_markdown_file` — ingest a small test .md file into a `_test_live` collection
- `test_query_returns_results` — query the ingested collection, verify results come back
- `test_cleanup` — delete the `_test_live` collection

This uses the full RAG pipeline (ingester → embedder → ChromaDB → retriever) with real services.

### T5: `corpus doctor` CLI Command
**Files:** `src/tools/rag/cli.py` (MODIFY), `src/tools/rag/doctor.py` (NEW)
**Complexity:** M
**Depends on:** none

Add `corpus rag doctor` command that runs connectivity checks and reports status:
```
$ corpus rag doctor
✓ Config loaded: configs/base.yaml
✓ ChromaDB reachable: localhost:8001 (5 collections)
✓ Ollama reachable: localhost:11434
✓ LLM model available: gemma4:26b-a4b-it-q4_K_M
✓ Embedding model available: embeddinggemma
✓ Test embedding: 768 dimensions
✗ Collection 'rag_notes' has 0 documents — did you run ingest?
```

### T6: Pytest Marker Configuration
**Files:** `pyproject.toml` (MODIFY)
**Complexity:** S
**Depends on:** T1

Add marker registration and default exclusion:
```toml
[tool.pytest.ini_options]
markers = ["live: tests requiring running ChromaDB and Ollama (deselect by default)"]
addopts = "-v --tb=short -m 'not live'"
```

Users run live tests with: `pytest -m live` or `pytest tests/live/`

## New Dependencies

None — uses `httpx` (already in deps) for connectivity checks.

## File Change Summary

| File | Task | Action |
|------|------|--------|
| `tests/live/__init__.py` | T1 | NEW |
| `tests/live/conftest.py` | T1 | NEW |
| `tests/live/test_chromadb.py` | T2 | NEW |
| `tests/live/test_ollama.py` | T3 | NEW |
| `tests/live/test_rag_pipeline.py` | T4 | NEW |
| `src/tools/rag/doctor.py` | T5 | NEW |
| `src/tools/rag/cli.py` | T5 | MODIFY |
| `pyproject.toml` | T6 | MODIFY |

## Open Questions

1. Should `corpus doctor` also check disk space for parent_store and scratch_dir?
2. Should live tests auto-skip individual tests if only one service is down (e.g., Ollama down but ChromaDB up)?
   - **Decision:** Yes — each test file skips independently based on what it needs.
