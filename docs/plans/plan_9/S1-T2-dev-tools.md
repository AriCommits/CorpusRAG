# T2: Create Dev Tools — `mcp_server/tools/dev.py`

**Sprint:** 1 (Parallel)
**Time:** 2 hrs
**Prerequisites:** None (T1 creates common.py, but dev.py can inline its own config/db init temporarily; final wiring happens in T4)
**Parallel-safe with:** T1, T3 (all create NEW files, zero overlap)

---

## Goal

Create standalone, transport-agnostic functions for the developer-focused MCP tools: RAG ingest, query, retrieve, **store_text** (new), and collection management. Each function takes explicit `config` and `db` arguments — no global state, no auth.

---

## Files to Create

| File | Action |
|------|--------|
| `src/mcp_server/tools/dev.py` | NEW — dev tool functions |
| `tests/unit/test_mcp_dev_tools.py` | NEW — unit tests |

---

## Design

### Public API

```python
def rag_ingest(path: str, collection: str, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Ingest documents from a file/directory into a RAG collection."""

def rag_query(collection: str, query: str, top_k: int, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Query a RAG collection and generate a response."""

def rag_retrieve(collection: str, query: str, top_k: int, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Retrieve relevant chunks without generating a response."""

def store_text(text: str, collection: str, config: BaseConfig, db: DatabaseBackend, metadata: dict | None = None) -> dict:
    """Store arbitrary text into a RAG collection. NEW — enables agents to push context."""

def list_collections(db: DatabaseBackend) -> dict:
    """List all available collections."""

def collection_info(collection_name: str, db: DatabaseBackend) -> dict:
    """Get info about a specific collection."""
```

### Key Constraints

- **No FastAPI imports** — pure functions
- **No auth** — auth is handled by middleware/profiles layer
- **Explicit deps** — every function receives `config` and `db` as args
- **Return dicts** — all functions return `{"status": "success", ...}` or `{"status": "error", "error": "..."}`
- **Input validation** — use `validate_query`, `validate_collection` from common.py (import from `mcp_server.tools.common` or inline the validation using `utils.validation` directly since T1 may not be merged yet)

---

## Implementation Details

### `store_text` — The Key New Tool

This is the most important new capability. It lets an agent store arbitrary text (plans, session summaries, code snippets) into the RAG knowledge base without needing a file on disk.

```python
def store_text(
    text: str,
    collection: str,
    config: BaseConfig,
    db: DatabaseBackend,
    metadata: dict | None = None,
) -> dict:
    """Store arbitrary text directly into a RAG collection.

    This enables agents to push context, plans, session summaries,
    and code snippets into the knowledge base for later retrieval.

    Args:
        text: Text content to store.
        collection: Target collection name.
        config: Base configuration.
        db: Database backend.
        metadata: Optional metadata dict (e.g., {"type": "plan", "project": "foo"}).

    Returns:
        Dict with status, collection, and chunks_created count.
    """
```

Implementation approach:
1. Create a `RAGConfig` from the base config
2. Build the full collection name with prefix
3. Create collection if it doesn't exist
4. Use `RecursiveCharacterTextSplitter` to chunk the text (same settings as `RAGIngester`)
5. Use `EmbeddingClient` to embed chunks
6. Store with metadata including `source_type: "agent_text"` and a timestamp
7. Return chunk count

### Other Functions

Extract the logic from the current `server.py` tool functions, but:
- Remove `auth_context` parameter
- Remove `Depends()` references
- Remove `auth_context["key_info"]["name"]` from return values
- Use `validate_query`/`validate_collection` for input validation
- Convert `SecurityError` to dict returns with `"status": "error"`

---

## Reference: Current server.py Functions to Extract From

The current `rag_ingest` in `server.py` (lines ~95-120):
- Validates file path via `utils.security.validate_file_path`
- Creates `RAGConfig.from_dict(config.to_dict())`
- Creates `RAGIngester(rag_config, db)`
- Calls `ingester.ingest_path()`
- Returns dict with status, collection, documents_processed, chunks_created

The current `rag_query` (lines ~122-155):
- Validates query and top_k via `get_validator()`
- Creates `RAGConfig` and `RAGAgent`
- Calls `agent.query()`
- Returns dict with status, query, response

The current `rag_retrieve` (lines ~157-195):
- Same validation pattern
- Creates `RAGRetriever`
- Returns list of chunks with text, source, score

---

## Tests

### `tests/unit/test_mcp_dev_tools.py`

Test each function with a temporary ChromaDB. Mock the LLM/embedding calls where needed.

```python
"""Tests for mcp_server.tools.dev — developer MCP tools."""

import pytest
import yaml

from config.base import BaseConfig


@pytest.fixture()
def dev_config(tmp_path):
    """Create config and DB for dev tool tests."""
    cfg_data = {
        "llm": {"model": "test-model"},
        "database": {
            "mode": "persistent",
            "persist_directory": str(tmp_path / "chroma"),
        },
        "rag": {
            "chunking": {"child_chunk_size": 200, "child_chunk_overlap": 20},
            "retrieval": {"top_k_semantic": 5, "top_k_bm25": 5, "top_k_final": 5, "rrf_k": 60},
            "parent_store": {"type": "local_file", "path": str(tmp_path / "parents")},
            "collection_prefix": "rag",
        },
    }
    cfg_path = tmp_path / "base.yaml"
    cfg_path.write_text(yaml.dump(cfg_data))
    return str(cfg_path)


class TestListCollections:
    def test_returns_dict_with_collections_key(self, dev_config):
        from db import ChromaDBBackend
        from config import load_config
        from mcp_server.tools.dev import list_collections

        config = load_config(dev_config)
        db = ChromaDBBackend(config.database)
        result = list_collections(db)
        assert result["status"] == "success"
        assert "collections" in result


class TestCollectionInfo:
    def test_nonexistent_collection(self, dev_config):
        from db import ChromaDBBackend
        from config import load_config
        from mcp_server.tools.dev import collection_info

        config = load_config(dev_config)
        db = ChromaDBBackend(config.database)
        result = collection_info("nonexistent", db)
        assert result["status"] == "error"


class TestStoreText:
    def test_stores_and_returns_chunk_count(self, dev_config):
        """Test that store_text creates chunks from raw text."""
        from db import ChromaDBBackend
        from config import load_config
        from mcp_server.tools.dev import store_text
        from unittest.mock import patch

        config = load_config(dev_config)
        db = ChromaDBBackend(config.database)

        # Mock embeddings since we don't have a real embedding model in tests
        fake_embedding = [0.1] * 384
        with patch(
            "mcp_server.tools.dev.EmbeddingClient.embed_texts",
            return_value=[fake_embedding],
        ):
            result = store_text(
                text="This is a test plan for implementing feature X.",
                collection="plans",
                config=config,
                db=db,
                metadata={"type": "plan", "project": "test"},
            )

        assert result["status"] == "success"
        assert result["chunks_created"] >= 1


class TestRagIngest:
    def test_invalid_path_returns_error(self, dev_config):
        from db import ChromaDBBackend
        from config import load_config
        from mcp_server.tools.dev import rag_ingest

        config = load_config(dev_config)
        db = ChromaDBBackend(config.database)
        result = rag_ingest("/nonexistent/path", "test", config, db)
        assert result["status"] == "error"
```

---

## Session Prompt

```
I'm implementing Plan 9, Task T2 from docs/plans/plan_9/S1-T2-dev-tools.md.

Goal: Create mcp_server/tools/dev.py with developer-focused MCP tool functions.

Please:
1. Read docs/plans/plan_9/S1-T2-dev-tools.md completely
2. Read src/mcp_server/server.py to see the current rag_ingest, rag_query, rag_retrieve implementations
3. Read src/tools/rag/ingest.py to understand the ingestion pipeline (needed for store_text)
4. Create src/mcp_server/tools/dev.py with all 6 functions from the plan
5. The store_text function should:
   - Use RecursiveCharacterTextSplitter and EmbeddingClient from tools.rag.pipeline
   - Create the collection if it doesn't exist
   - Add source_type="agent_text" and a timestamp to metadata
   - Return {"status": "success", "collection": ..., "chunks_created": N}
6. For input validation, import directly from utils.validation and utils.security
   (common.py from T1 may not be merged yet)
7. Create tests/unit/test_mcp_dev_tools.py
8. Run tests and fix issues

Key constraint: NO FastAPI imports. NO auth parameters. All functions take explicit config + db args.
```

---

## Verification

```bash
pytest tests/unit/test_mcp_dev_tools.py -v

# No FastAPI imports
grep -r "fastapi" src/mcp_server/tools/dev.py && echo "FAIL" || echo "PASS"

# store_text function exists
python -c "from mcp_server.tools.dev import store_text; print('PASS')"
```

---

## Done When

- [ ] `src/mcp_server/tools/dev.py` has all 6 functions
- [ ] `store_text` can chunk, embed, and store arbitrary text
- [ ] All functions return `{"status": "success"|"error", ...}` dicts
- [ ] No FastAPI imports
- [ ] `tests/unit/test_mcp_dev_tools.py` passes
- [ ] Existing tests still pass
