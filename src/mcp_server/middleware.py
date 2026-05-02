"""HTTP-specific middleware for MCP server. Only used with streamable-http transport."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_http_middleware(mcp, auth_enabled: bool = True) -> None:
    """Apply HTTP-specific middleware. Only call for streamable-http transport."""
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware

    if not hasattr(mcp, "app") or not isinstance(mcp.app, FastAPI):
        logger.warning("No FastAPI app found; skipping HTTP middleware.")
        return

    app = mcp.app

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000", "http://localhost:8888"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "X-API-Key", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    if auth_enabled:
        _apply_auth(app)

    _add_health_endpoints(app)


def _apply_auth(app) -> None:
    from starlette.responses import JSONResponse
    from utils.auth import AuthConfig, MCPAuthenticator
    auth_config = AuthConfig(enabled=True, api_keys={}, rate_limit_enabled=True, requests_per_minute=100, requests_per_hour=1000)
    auth_file = Path.home() / ".corpusrag" / "api_keys.json"
    authenticator = MCPAuthenticator(auth_config, auth_file)
    if not authenticator.api_key_manager.api_keys:
        admin_key = authenticator.create_admin_key()
        logger.info("Admin API key generated: %s...%s", admin_key[:4], admin_key[-4:])

    @app.middleware("http")
    async def auth_middleware(request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)
        api_key = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix("Bearer ")
        if not authenticator.api_key_manager.validate_api_key(api_key):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


def _add_health_endpoints(app) -> None:
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "corpusrag-mcp"}

    @app.get("/health/ready")
    async def readiness_check():
        return {"status": "ready"}
