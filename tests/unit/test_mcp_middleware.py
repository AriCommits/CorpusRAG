import pytest


class TestMiddlewareImport:
    def test_module_importable(self):
        from mcp_server.middleware import apply_http_middleware
        assert callable(apply_http_middleware)


class TestApplyHttpMiddleware:
    def test_applies_without_error(self):
        from mcp.server.fastmcp import FastMCP
        from mcp_server.middleware import apply_http_middleware
        mcp = FastMCP("test")
        apply_http_middleware(mcp, auth_enabled=False)


class TestAuthLazyImports:
    def test_no_toplevel_fastapi(self):
        import ast
        from pathlib import Path
        source = Path("src/utils/auth.py").read_text()
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "fastapi" not in node.module.lower(), f"Top-level FastAPI import: {node.module}"
