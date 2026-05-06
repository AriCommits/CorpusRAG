# Sprint 1 — All Tasks (Fully Parallel)

**Plan:** docs/plans/plan_17/OVERVIEW.md
**Wave:** 1 of 1
**Can run in parallel with:** All agents — zero file conflicts

All 6 tasks create new files or modify different files. No conflicts.

---

### Agent A: T1 + T6 — Shared Fixtures + Pytest Config

**Complexity:** M
**Estimated time:** 1 hour
**Files:**
- `tests/live/__init__.py` (NEW)
- `tests/live/conftest.py` (NEW)
- `pyproject.toml` (MODIFY) — add `live` marker, update addopts

**Instructions:**
Create `tests/live/__init__.py` (empty).

Create `tests/live/conftest.py`:
```python
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
    """Check Ollama is reachable."""
    import httpx
    endpoint = live_config.llm.endpoint
    try:
        r = httpx.get(f"{endpoint}/api/tags", timeout=5)
        if r.status_code != 200:
            pytest.skip("Ollama not healthy")
        return r.json()
    except Exception:
        pytest.skip(f"Ollama not reachable at {endpoint}")
```

Modify `pyproject.toml` — in `[tool.pytest.ini_options]`:
- Add: `markers = ["live: tests requiring running ChromaDB and Ollama"]`
- Change addopts from `"-v --tb=short"` to `"-v --tb=short -m \"not live\""`

**Definition of Done:**
- [ ] `tests/live/conftest.py` exists with 3 session-scoped fixtures
- [ ] `pytest` (no args) skips live tests
- [ ] `pytest -m live` selects live tests
- [ ] `pytest tests/live/` also works

---

### Agent B: T2 — ChromaDB Connectivity Tests

**Complexity:** S
**Estimated time:** 30 min
**Files:**
- `tests/live/test_chromadb.py` (NEW)

**Instructions:**
```python
"""Live tests for ChromaDB connectivity."""

import pytest

pytestmark = pytest.mark.live

TEST_COLLECTION = "_test_live_probe"


def test_chromadb_heartbeat(live_config):
    import httpx
    host = live_config.database.host
    port = live_config.database.port
    r = httpx.get(f"http://{host}:{port}/api/v2/heartbeat", timeout=5)
    assert r.status_code == 200


def test_list_collections(live_db):
    collections = live_db.list_collections()
    assert isinstance(collections, list)


def test_create_and_delete_collection(live_db):
    if live_db.collection_exists(TEST_COLLECTION):
        live_db.delete_collection(TEST_COLLECTION)
    live_db.create_collection(TEST_COLLECTION)
    assert live_db.collection_exists(TEST_COLLECTION)
    live_db.delete_collection(TEST_COLLECTION)
    assert not live_db.collection_exists(TEST_COLLECTION)


def test_add_and_query_document(live_db, live_config):
    """Add a document with a real embedding and query it back."""
    from tools.rag.pipeline import EmbeddingClient
    from tools.rag.config import RAGConfig

    rag_config = RAGConfig.from_dict(live_config.to_dict())
    embedder = EmbeddingClient(rag_config)

    collection = TEST_COLLECTION
    if live_db.collection_exists(collection):
        live_db.delete_collection(collection)
    live_db.create_collection(collection)

    try:
        text = "The mitochondria is the powerhouse of the cell."
        embedding = embedder.embed_texts([text])[0]
        assert len(embedding) > 0, "Embedding should have dimensions"

        live_db.add_documents(
            collection=collection,
            documents=[text],
            embeddings=[embedding],
            metadata=[{"source": "test"}],
            ids=["test_doc_1"],
        )

        results = live_db.query(collection, embedding, n_results=1)
        assert len(results["ids"][0]) > 0
        assert "mitochondria" in results["documents"][0][0].lower()
    finally:
        live_db.delete_collection(collection)
```

**Definition of Done:**
- [ ] All 4 tests pass when ChromaDB is running on port 8001
- [ ] Tests skip gracefully when ChromaDB is down

---

### Agent C: T3 — Ollama Connectivity Tests

**Complexity:** S
**Estimated time:** 30 min
**Files:**
- `tests/live/test_ollama.py` (NEW)

**Instructions:**
```python
"""Live tests for Ollama connectivity."""

import pytest

pytestmark = pytest.mark.live


def test_ollama_reachable(live_config):
    import httpx
    r = httpx.get(f"{live_config.llm.endpoint}/api/tags", timeout=5)
    assert r.status_code == 200


def test_configured_model_available(live_config, ollama_available):
    models = [m["name"].split(":")[0] for m in ollama_available.get("models", [])]
    model_name = live_config.llm.model.split(":")[0]
    assert model_name in models, f"{live_config.llm.model} not found. Available: {models}"


def test_embedding_model_available(live_config, ollama_available):
    models = [m["name"].split(":")[0] for m in ollama_available.get("models", [])]
    embed_model = live_config.embedding.model.split(":")[0]
    assert embed_model in models, f"{live_config.embedding.model} not found. Available: {models}"


def test_generate_response(live_config):
    import httpx
    r = httpx.post(
        f"{live_config.llm.endpoint}/api/generate",
        json={"model": live_config.llm.model, "prompt": "Say hello.", "stream": False},
        timeout=60,
    )
    assert r.status_code == 200
    assert len(r.json().get("response", "")) > 0


def test_embed_text(live_config):
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
```

**Definition of Done:**
- [ ] All 5 tests pass when Ollama is running with configured models
- [ ] Tests skip when Ollama is down

---

### Agent D: T4 — End-to-End RAG Pipeline Test

**Complexity:** M
**Estimated time:** 1 hour
**Files:**
- `tests/live/test_rag_pipeline.py` (NEW)

**Instructions:**
```python
"""Live end-to-end RAG pipeline test."""

import pytest
from pathlib import Path

pytestmark = pytest.mark.live

TEST_COLLECTION = "_test_live_rag"


@pytest.fixture
def test_doc(tmp_path):
    doc = tmp_path / "test_notes.md"
    doc.write_text(
        "# Photosynthesis\n\n"
        "Photosynthesis is the process by which plants convert sunlight into energy.\n"
        "It occurs in the chloroplasts and produces glucose and oxygen.\n\n"
        "## Light Reactions\n\n"
        "The light reactions occur in the thylakoid membranes.\n"
    )
    return doc


def test_ingest_and_query(live_config, live_db, test_doc):
    """Full pipeline: ingest a file, query it, verify results."""
    from tools.rag import RAGConfig, RAGIngester, RAGRetriever

    rag_config = RAGConfig.from_dict(live_config.to_dict())

    # Cleanup from previous runs
    full_name = f"{rag_config.collection_prefix}_{TEST_COLLECTION}"
    if live_db.collection_exists(full_name):
        live_db.delete_collection(full_name)

    try:
        # Ingest
        ingester = RAGIngester(rag_config, live_db)
        result = ingester.ingest_path(str(test_doc.parent), TEST_COLLECTION)
        assert result.files_indexed >= 1
        assert result.chunks_indexed >= 1

        # Query
        retriever = RAGRetriever(rag_config, live_db)
        docs = retriever.retrieve("What is photosynthesis?", TEST_COLLECTION, top_k=3)
        assert len(docs) > 0
        assert any("photosynthesis" in d.text.lower() for d in docs)
    finally:
        if live_db.collection_exists(full_name):
            live_db.delete_collection(full_name)
```

**Definition of Done:**
- [ ] Test passes with real ChromaDB + Ollama
- [ ] Cleans up after itself
- [ ] Verifies the full ingest → embed → store → retrieve pipeline

---

### Agent E: T5 — `corpus rag doctor` Command

**Complexity:** M
**Estimated time:** 1.5 hours
**Files:**
- `src/tools/rag/doctor.py` (NEW)
- `src/tools/rag/cli.py` (MODIFY) — add `doctor` command

**Instructions:**
Create `src/tools/rag/doctor.py`:
```python
"""Health check diagnostics for CorpusRAG."""

import httpx
from pathlib import Path
from tools.rag.config import RAGConfig
from db import ChromaDBBackend


def run_doctor(config: RAGConfig) -> list[tuple[bool, str]]:
    """Run all health checks. Returns list of (passed, message)."""
    results = []

    # 1. Config loaded
    results.append((True, f"Config loaded: configs/base.yaml"))

    # 2. ChromaDB
    host, port = config.database.host, config.database.port
    try:
        r = httpx.get(f"http://{host}:{port}/api/v2/heartbeat", timeout=5)
        if r.status_code == 200:
            db = ChromaDBBackend(config.database)
            cols = db.list_collections()
            results.append((True, f"ChromaDB reachable: {host}:{port} ({len(cols)} collections)"))
        else:
            results.append((False, f"ChromaDB unhealthy: {host}:{port} (status {r.status_code})"))
    except Exception as e:
        results.append((False, f"ChromaDB unreachable: {host}:{port} — {e}"))

    # 3. Ollama
    endpoint = config.llm.endpoint
    try:
        r = httpx.get(f"{endpoint}/api/tags", timeout=5)
        if r.status_code == 200:
            results.append((True, f"Ollama reachable: {endpoint}"))
            models = [m["name"] for m in r.json().get("models", [])]
            model_names = [m.split(":")[0] for m in models]

            # 4. LLM model
            llm_model = config.llm.model.split(":")[0]
            if llm_model in model_names:
                results.append((True, f"LLM model available: {config.llm.model}"))
            else:
                results.append((False, f"LLM model NOT found: {config.llm.model} (available: {', '.join(models)})"))

            # 5. Embedding model
            embed_model = config.embedding.model.split(":")[0]
            if embed_model in model_names:
                results.append((True, f"Embedding model available: {config.embedding.model}"))
            else:
                results.append((False, f"Embedding model NOT found: {config.embedding.model} (available: {', '.join(models)})"))

            # 6. Test embedding
            try:
                er = httpx.post(
                    f"{endpoint}/api/embed",
                    json={"model": config.embedding.model, "input": "test"},
                    timeout=30,
                )
                if er.status_code == 200:
                    dims = len(er.json().get("embeddings", [[]])[0])
                    results.append((True, f"Test embedding: {dims} dimensions"))
                else:
                    results.append((False, f"Embedding failed: status {er.status_code}"))
            except Exception as e:
                results.append((False, f"Embedding failed: {e}"))
        else:
            results.append((False, f"Ollama unhealthy: {endpoint}"))
    except Exception as e:
        results.append((False, f"Ollama unreachable: {endpoint} — {e}"))

    return results
```

Add to `src/tools/rag/cli.py` — add a `doctor` command to the `rag` group (use lazy import):
```python
@rag.command()
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def doctor(config):
    """Run health checks against configured services."""
    from cli_common import load_cli_config
    from tools.rag.config import RAGConfig
    from tools.rag.doctor import run_doctor

    cfg = load_cli_config(config, RAGConfig)
    results = run_doctor(cfg)

    for passed, msg in results:
        icon = "✓" if passed else "✗"
        click.echo(f"  {icon} {msg}")

    failures = sum(1 for p, _ in results if not p)
    if failures:
        click.echo(f"\n{failures} check(s) failed.")
        raise SystemExit(1)
    else:
        click.echo(f"\nAll checks passed!")
```

**Definition of Done:**
- [ ] `corpus rag doctor` runs and reports status
- [ ] Shows ✓/✗ for each check
- [ ] Exits with code 1 if any check fails
- [ ] Uses lazy imports (doesn't slow down `corpus --help`)
