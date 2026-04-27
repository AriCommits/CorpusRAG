# T6: Rewrite `mcp_server/server.py` as Thin Orchestrator

**Sprint:** 3 (Parallel with T7)
**Time:** 1.5 hrs
**Prerequisites:** T1-T5 all merged
**Parallel-safe with:** T7 (different files)

---

## Goal

Replace the monolithic 570-line `server.py` with a thin ~80-line orchestrator that wires together profiles, transport, and middleware. This is the integration point where everything comes together.

---

## Files to Modify

| File | Action |
|------|--------|
| `src/mcp_server/server.py` | REWRITE — thin orchestrator |
| `src/mcp_server/__init__.py` | MODIFY — update exports |
| `tests/unit/test_mcp_server.py` | REWRITE — test new structure |
| `tests/test_mcp_tools.py` | REWRITE — test new structure |

---

## Design

### New `server.py` Structure

```python
"""CorpusRAG MCP Server.

Thin orchestrator that wires together:
- Tool profiles (dev/learn/full)
- Transport (stdio/streamable-http)
- Middleware (auth, CORS — HTTP only)
"""

import argparse
import logging

from mcp.server.fastmcp import FastMCP

from .profiles import VALID_PROFILES, register_profile
from .tools.common import init_config, init_db

logger = logging.getLogger(__name__)


def create_mcp_server(
    config_path: str | None = None,
    profile: str = "full",
) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        config_path: Path to config YAML. Defaults to configs/base.yaml.
        profile: Tool profile — "dev", "learn", or "full".

    Returns:
        Configured FastMCP server instance.
    """
    config = init_config(config_path)
    db = init_db(config)

    mcp = FastMCP("CorpusRAG", json_response=True)
    register_profile(mcp, profile, config, db)

    logger.info("MCP server created with profile='%s'", profile)
    return mcp


def main() -> None:
    """CLI entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="CorpusRAG MCP Server")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument(
        "--profile",
        choices=list(VALID_PROFILES),
        default="full",
        help="Tool profile (default: full)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host (HTTP only)")
    parser.add_argument("--port", type=int, default=8000, help="Port (HTTP only)")
    parser.add_argument(
        "--no-auth", action="store_true", help="Disable auth (HTTP only)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    mcp = create_mcp_server(args.config, args.profile)

    if args.transport == "streamable-http":
        from .middleware import apply_http_middleware

        apply_http_middleware(mcp, auth_enabled=not args.no_auth)
        logger.info(
            "Starting CorpusRAG MCP (HTTP) on %s:%d [profile=%s]",
            args.host, args.port, args.profile,
        )
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        logger.info("Starting CorpusRAG MCP (stdio) [profile=%s]", args.profile)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

### Key Changes from Current server.py

| Aspect | Before (570 lines) | After (~80 lines) |
|--------|--------------------|--------------------|
| Tool definitions | Inline in server.py | In tools/dev.py, tools/learn.py |
| Tool registration | All tools always registered | Profile-based via profiles.py |
| Auth | Hardcoded FastAPI Depends() on every tool | Optional, HTTP-only via middleware.py |
| Transport | HTTP only (streamable-http default) | stdio default, HTTP optional |
| Config/DB init | Inline in create_mcp_server | Delegated to tools/common.py |
| Health endpoints | Inline in main() | In middleware.py |
| CORS/headers | Inline in create_mcp_server | In middleware.py |

### Updated `__init__.py`

```python
"""MCP Server for CorpusRAG."""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
```

No change needed — same export, but now `create_mcp_server` accepts a `profile` parameter.

---

## Tests

### Rewritten `tests/unit/test_mcp_server.py`

```python
"""Tests for MCP server creation and profile loading."""

import asyncio

import pytest
import yaml

from mcp_server import create_mcp_server


@pytest.fixture()
def config_file(tmp_path):
    cfg = {
        "llm": {"model": "test"},
        "database": {"mode": "persistent", "persist_directory": str(tmp_path / "chroma")},
    }
    path = tmp_path / "base.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


class TestCreateMcpServer:
    def test_creates_server(self, config_file):
        server = create_mcp_server(config_file)
        assert server is not None
        assert server.name == "CorpusRAG"

    def test_dev_profile(self, config_file):
        server = create_mcp_server(config_file, profile="dev")
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "rag_query" in names
        assert "store_text" in names
        assert "generate_flashcards" not in names

    def test_learn_profile(self, config_file):
        server = create_mcp_server(config_file, profile="learn")
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "generate_flashcards" in names
        assert "rag_query" not in names

    def test_full_profile(self, config_file):
        server = create_mcp_server(config_file, profile="full")
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "rag_query" in names
        assert "generate_flashcards" in names

    def test_default_profile_is_full(self, config_file):
        server = create_mcp_server(config_file)
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "rag_query" in names
        assert "generate_flashcards" in names
```

### Rewritten `tests/test_mcp_tools.py`

Keep the input validation tests (they test `utils.validation` which hasn't changed), but update the MCP server import tests to use the new `profile` parameter.

---

## Session Prompt

```
I'm implementing Plan 9, Task T6 from docs/plans/plan_9/S3-T6-server-rewrite.md.

Goal: Replace the monolithic mcp_server/server.py with a thin orchestrator.

Please:
1. Read docs/plans/plan_9/S3-T6-server-rewrite.md completely
2. Read the current src/mcp_server/server.py (the old 570-line version)
3. Read the new files created in T1-T5:
   - src/mcp_server/tools/common.py
   - src/mcp_server/tools/dev.py
   - src/mcp_server/tools/learn.py
   - src/mcp_server/profiles.py
   - src/mcp_server/middleware.py
4. REPLACE src/mcp_server/server.py with the thin orchestrator from the plan
5. Update src/mcp_server/__init__.py if needed
6. REWRITE tests/unit/test_mcp_server.py with the new tests
7. UPDATE tests/test_mcp_tools.py — keep validation tests, update server import tests
8. Run ALL tests and fix issues

Key changes:
- Default transport is now "stdio" (was "streamable-http")
- create_mcp_server() now accepts profile parameter
- No FastAPI imports at top level of server.py
- middleware.py is only imported inside the HTTP branch
```

---

## Verification

```bash
# New tests pass
pytest tests/unit/test_mcp_server.py -v
pytest tests/test_mcp_tools.py -v

# Server module is small
python -c "
lines = len(open('src/mcp_server/server.py').readlines())
assert lines < 120, f'server.py is {lines} lines, expected < 120'
print(f'PASS: server.py is {lines} lines')
"

# No top-level FastAPI imports in server.py
python -c "
import ast
source = open('src/mcp_server/server.py').read()
tree = ast.parse(source)
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.ImportFrom) and node.module and 'fastapi' in node.module.lower():
        print(f'FAIL: top-level FastAPI import')
        exit(1)
print('PASS: No top-level FastAPI imports')
"

# All tests pass
pytest tests/ -v --tb=short
```

---

## Done When

- [ ] `src/mcp_server/server.py` is < 120 lines
- [ ] `create_mcp_server(profile="dev")` only registers dev tools
- [ ] Default transport is `stdio`
- [ ] HTTP transport conditionally imports middleware
- [ ] No top-level FastAPI imports in server.py
- [ ] `tests/unit/test_mcp_server.py` passes with new tests
- [ ] `tests/test_mcp_tools.py` passes (updated)
- [ ] All existing tests still pass
