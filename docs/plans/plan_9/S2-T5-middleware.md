# T5: Create Transport-Aware Middleware — `mcp_server/middleware.py`

**Sprint:** 2 (Parallel with T4)
**Time:** 1.5 hrs
**Prerequisites:** T1 merged (uses common.py patterns)
**Parallel-safe with:** T4 (different files)

---

## Goal

Decouple authentication and HTTP middleware from tool logic. Auth only applies when using HTTP transport. Stdio transport skips auth entirely. Refactor `utils/auth.py` to not import FastAPI at module level.

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/mcp_server/middleware.py` | NEW — transport-aware middleware |
| `src/utils/auth.py` | MODIFY — lazy FastAPI imports |

---

## Design

### `middleware.py` Public API

```python
def apply_http_middleware(mcp: FastMCP, auth_enabled: bool = True) -> None:
    """Apply HTTP-specific middleware to the MCP server.

    Only call this when transport is streamable-http.
    Adds: CORS, security headers, and optional API key auth.

    Args:
        mcp: FastMCP server instance (must have a FastAPI .app attribute).
        auth_enabled: Whether to enable API key authentication.
    """
```

### Key Constraints

- **`middleware.py` is only imported/called for HTTP transport** — server.py conditionally calls it
- **stdio transport never touches this module** — no auth overhead for editor integrations
- **`utils/auth.py` must not import FastAPI at module level** — move FastAPI imports inside methods

---

## Implementation Details

### `src/mcp_server/middleware.py`

```python
"""HTTP-specific middleware for MCP server.

This module is ONLY used when transport is streamable-http.
It is never imported for stdio transport.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_http_middleware(mcp, auth_enabled: bool = True) -> None:
    """Apply HTTP-specific middleware to the MCP server.

    Adds CORS, security headers, and optional API key authentication.
    Only call when using streamable-http transport.

    Args:
        mcp: FastMCP server instance.
        auth_enabled: Whether to enable API key authentication.
    """
    # Lazy import — only needed for HTTP
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware

    if not hasattr(mcp, "app") or not isinstance(mcp.app, FastAPI):
        logger.warning("MCP server does not have a FastAPI app; skipping HTTP middleware.")
        return

    app = mcp.app

    # CORS — restrict to localhost origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8888",
            "https://localhost:3000",
            "https://localhost:8000",
            "https://localhost:8888",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "X-API-Key", "Content-Type"],
    )

    # Security headers
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    # Auth (optional)
    if auth_enabled:
        _apply_auth(mcp)

    # Health endpoints
    _add_health_endpoints(app)

    logger.info("HTTP middleware applied (CORS, security headers, auth=%s)", auth_enabled)


def _apply_auth(mcp) -> None:
    """Set up API key authentication for HTTP transport."""
    from utils.auth import AuthConfig, MCPAuthenticator

    auth_config = AuthConfig(
        enabled=True,
        api_keys={},
        rate_limit_enabled=True,
        requests_per_minute=100,
        requests_per_hour=1000,
    )

    auth_file = Path.home() / ".corpusrag" / "api_keys.json"
    authenticator = MCPAuthenticator(auth_config, auth_file)

    if not authenticator.api_key_manager.api_keys:
        admin_key = authenticator.create_admin_key()
        logger.info("Generated admin API key: %s", admin_key)
        logger.info("Store this key securely — it won't be displayed again!")


def _add_health_endpoints(app) -> None:
    """Add health check endpoints for container orchestration."""

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "corpusrag-mcp",
            "version": "0.6.0",
        }

    @app.get("/health/ready")
    async def readiness_check():
        return {"status": "ready"}
```

### Refactoring `utils/auth.py`

The current `utils/auth.py` has these top-level imports that break stdio:

```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
```

Move these inside the methods that use them:

```python
# BEFORE (top of file):
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# AFTER (top of file):
# No FastAPI imports at module level

# AFTER (inside MCPAuthenticator.__init__):
def __init__(self, config, config_file=None):
    from fastapi.security import HTTPBearer  # Lazy import
    self.security = HTTPBearer(auto_error=False)
    ...

# AFTER (inside authenticate_request):
async def authenticate_request(self, request, credentials=None):
    from fastapi import HTTPException  # Lazy import
    ...
```

The key changes to `utils/auth.py`:
1. Remove the 2 FastAPI import lines from the top of the file
2. Add `from fastapi import HTTPException` inside `authenticate_request()`
3. Add `from fastapi.security import HTTPBearer` inside `__init__()`
4. Update the `authenticate_request` signature to not use `Depends()` at the module level — the `Depends()` wiring is now in `middleware.py`

---

## Tests

Test that:
1. `middleware.py` can be imported without FastAPI being required at import time
2. `apply_http_middleware` works when given a FastMCP with a FastAPI app
3. stdio transport doesn't trigger any FastAPI imports

```python
"""Tests for mcp_server.middleware — HTTP-specific middleware."""

import pytest


class TestMiddlewareImport:
    def test_module_importable(self):
        """middleware.py should import without errors."""
        from mcp_server.middleware import apply_http_middleware
        assert callable(apply_http_middleware)


class TestApplyHttpMiddleware:
    def test_applies_to_fastmcp(self, tmp_path):
        """Test middleware applies to a real FastMCP instance."""
        import yaml
        from mcp.server.fastmcp import FastMCP
        from mcp_server.middleware import apply_http_middleware

        mcp = FastMCP("test")
        # apply_http_middleware should not raise
        apply_http_middleware(mcp, auth_enabled=False)


class TestAuthLazyImports:
    def test_auth_module_no_toplevel_fastapi(self):
        """utils/auth.py should not import FastAPI at module level."""
        import ast
        from pathlib import Path

        source = Path("src/utils/auth.py").read_text()
        tree = ast.parse(source)

        # Check only top-level imports (not inside functions/classes)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "fastapi" not in node.module.lower(), (
                    f"Top-level FastAPI import found: from {node.module}"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "fastapi" not in alias.name.lower(), (
                        f"Top-level FastAPI import found: import {alias.name}"
                    )
```

---

## Session Prompt

```
I'm implementing Plan 9, Task T5 from docs/plans/plan_9/S2-T5-middleware.md.

Goal: Create mcp_server/middleware.py and refactor utils/auth.py for lazy FastAPI imports.

Please:
1. Read docs/plans/plan_9/S2-T5-middleware.md completely
2. Read src/utils/auth.py — note the top-level FastAPI imports on lines 12-13
3. Read src/mcp_server/server.py lines 480-570 — the CORS, security headers, and health endpoint code
4. Create src/mcp_server/middleware.py with apply_http_middleware()
5. Refactor src/utils/auth.py:
   - Remove the 2 top-level FastAPI import lines
   - Add lazy imports inside the methods that need them
   - The Depends() pattern moves to profiles.py (T4), not here
6. Run existing tests to make sure nothing breaks
7. Create the test file

Critical: After this change, `import utils.auth` must NOT trigger FastAPI import.
```

---

## Verification

```bash
# New tests pass
pytest tests/unit/test_mcp_middleware.py -v  # or wherever tests land

# Auth module doesn't import FastAPI at top level
python -c "
import ast
source = open('src/utils/auth.py').read()
tree = ast.parse(source)
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.ImportFrom) and node.module and 'fastapi' in node.module.lower():
        print(f'FAIL: top-level import from {node.module}')
        exit(1)
print('PASS: No top-level FastAPI imports in auth.py')
"

# Existing tests still pass
pytest tests/ -v --tb=short
```

---

## Done When

- [ ] `src/mcp_server/middleware.py` exists with `apply_http_middleware()`
- [ ] `utils/auth.py` has no top-level FastAPI imports
- [ ] `import utils.auth` works without FastAPI installed (lazy imports)
- [ ] HTTP middleware adds CORS, security headers, health endpoints
- [ ] Existing tests still pass
