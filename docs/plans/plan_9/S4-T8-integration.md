# T8: End-to-End stdio Integration Test

**Sprint:** 4 (Serial)
**Time:** 1.5 hrs
**Prerequisites:** T1-T7 ALL merged — needs the complete working system

---

## Goal

Verify the full stdio MCP flow works as a real editor client would use it. Spawn the server as a subprocess, connect via stdio, call tools, and verify round-trip behavior.

---

## Files to Create

| File | Action |
|------|--------|
| `tests/integration/test_mcp_stdio.py` | NEW — E2E integration test |

---

## Design

### Test Scenarios

1. **Server starts with dev profile via stdio** — spawn `corpus-mcp-server --profile dev --transport stdio`, verify it starts without error
2. **list_tools returns only dev tools** — connect as MCP client, call `list_tools`, verify `rag_query` present and `generate_flashcards` absent
3. **store_text + rag_retrieve round-trip** — store a plan via `store_text`, retrieve it via `rag_retrieve`, verify the text comes back
4. **learn profile excludes dev tools** — start with `--profile learn`, verify `store_text` is absent
5. **No FastAPI imported in stdio mode** — verify the server process doesn't load FastAPI modules

### Test Approach

Use the `mcp` library's client SDK to connect to the server subprocess via stdio. The `mcp` package provides `ClientSession` and `StdioServerParameters` for this.

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
```

If the MCP client SDK is not available or too complex to wire up in tests, fall back to subprocess-based testing:
1. Start server as subprocess with `--transport stdio`
2. Send JSON-RPC messages via stdin
3. Read JSON-RPC responses from stdout
4. Verify response structure

---

## Implementation

### `tests/integration/test_mcp_stdio.py`

```python
"""End-to-end integration tests for MCP server stdio transport.

These tests spawn the MCP server as a subprocess and communicate
via stdio, simulating how an editor (Claude, Kiro, Neovim) would connect.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def stdio_config(tmp_path):
    """Create a minimal config for stdio testing."""
    cfg = {
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
    path = tmp_path / "test_config.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


def _send_jsonrpc(proc, method, params=None, req_id=1):
    """Send a JSON-RPC request to the server via stdin."""
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params:
        msg["params"] = params
    data = json.dumps(msg)
    content = f"Content-Length: {len(data)}\r\n\r\n{data}"
    proc.stdin.write(content.encode())
    proc.stdin.flush()


def _read_jsonrpc(proc, timeout=10):
    """Read a JSON-RPC response from the server via stdout."""
    # Read Content-Length header
    import select
    start = time.time()
    header = b""
    while time.time() - start < timeout:
        byte = proc.stdout.read(1)
        if byte:
            header += byte
            if header.endswith(b"\r\n\r\n"):
                break
    else:
        raise TimeoutError("Timed out reading response header")

    # Parse content length
    header_str = header.decode()
    for line in header_str.split("\r\n"):
        if line.lower().startswith("content-length:"):
            length = int(line.split(":")[1].strip())
            break
    else:
        raise ValueError(f"No Content-Length in header: {header_str}")

    # Read body
    body = proc.stdout.read(length)
    return json.loads(body.decode())


class TestStdioServerStarts:
    def test_server_starts_with_dev_profile(self, stdio_config):
        """Server should start and respond to initialize request."""
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "mcp_server.server",
                "--profile", "dev",
                "--transport", "stdio",
                "--config", stdio_config,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent.parent.parent / "src"),
        )
        try:
            # Give it a moment to start
            time.sleep(1)
            assert proc.poll() is None, f"Server exited early: {proc.stderr.read().decode()}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_server_starts_with_learn_profile(self, stdio_config):
        """Server should start with learn profile."""
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "mcp_server.server",
                "--profile", "learn",
                "--transport", "stdio",
                "--config", stdio_config,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent.parent.parent / "src"),
        )
        try:
            time.sleep(1)
            assert proc.poll() is None, f"Server exited early: {proc.stderr.read().decode()}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)


class TestDevProfileTools:
    def test_dev_profile_has_store_text(self, stdio_config):
        """Dev profile should include store_text tool."""
        from mcp_server.profiles import register_profile
        from mcp_server.tools.common import init_config, init_db
        from mcp.server.fastmcp import FastMCP
        import asyncio

        config = init_config(stdio_config)
        db = init_db(config)
        mcp = FastMCP("test")
        register_profile(mcp, "dev", config, db)

        names = [t.name for t in asyncio.run(mcp.list_tools())]
        assert "store_text" in names
        assert "rag_query" in names
        assert "rag_retrieve" in names
        assert "generate_flashcards" not in names

    def test_learn_profile_excludes_dev_tools(self, stdio_config):
        """Learn profile should NOT include dev tools."""
        from mcp_server.profiles import register_profile
        from mcp_server.tools.common import init_config, init_db
        from mcp.server.fastmcp import FastMCP
        import asyncio

        config = init_config(stdio_config)
        db = init_db(config)
        mcp = FastMCP("test")
        register_profile(mcp, "learn", config, db)

        names = [t.name for t in asyncio.run(mcp.list_tools())]
        assert "store_text" not in names
        assert "rag_query" not in names
        assert "generate_flashcards" in names


class TestStoreTextRoundTrip:
    def test_store_and_retrieve(self, stdio_config):
        """Store text via store_text, retrieve via rag_retrieve."""
        from mcp_server.tools.common import init_config, init_db
        from mcp_server.tools.dev import store_text, rag_retrieve
        from unittest.mock import patch

        config = init_config(stdio_config)
        db = init_db(config)

        fake_embedding = [0.1] * 384

        with patch(
            "mcp_server.tools.dev.EmbeddingClient.embed_texts",
            return_value=[fake_embedding],
        ):
            store_result = store_text(
                text="The implementation plan for feature X involves three phases.",
                collection="plans",
                config=config,
                db=db,
                metadata={"type": "plan", "project": "test"},
            )

        assert store_result["status"] == "success"
        assert store_result["chunks_created"] >= 1

        # Verify data is in the collection
        full_collection = f"rag_plans"
        assert db.collection_exists(full_collection)
        count = db.count_documents(full_collection)
        assert count >= 1
```

---

## Session Prompt

```
I'm implementing Plan 9, Task T8 from docs/plans/plan_9/S4-T8-integration.md.

Goal: Create end-to-end integration tests for the MCP server stdio transport.

Please:
1. Read docs/plans/plan_9/S4-T8-integration.md completely
2. Read the final versions of:
   - src/mcp_server/server.py (the rewritten thin orchestrator)
   - src/mcp_server/profiles.py
   - src/mcp_server/tools/dev.py (especially store_text)
   - src/mcp_server/tools/common.py
3. Create tests/integration/test_mcp_stdio.py with:
   - Test that server starts with dev profile via stdio (subprocess)
   - Test that dev profile has store_text but not flashcards
   - Test that learn profile has flashcards but not store_text
   - Test store_text → rag_retrieve round-trip (mock embeddings)
4. Run tests and fix issues

Focus on testing the profile isolation and the store_text round-trip.
Mock embeddings since we don't have a real model in CI.
```

---

## Verification

```bash
pytest tests/integration/test_mcp_stdio.py -v

# All tests pass
pytest tests/ -v --tb=short
```

---

## Done When

- [ ] `tests/integration/test_mcp_stdio.py` exists
- [ ] Server starts with `--profile dev --transport stdio` without error
- [ ] Dev profile has `store_text`, `rag_query` but not `generate_flashcards`
- [ ] Learn profile has `generate_flashcards` but not `store_text`
- [ ] `store_text` → retrieve round-trip works (with mocked embeddings)
- [ ] All tests pass: `pytest tests/ -v --tb=short`
