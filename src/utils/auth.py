"""Authentication and authorization module for MCP server."""

import json
import os
import secrets
import stat
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass
class AuthConfig:
    """Authentication configuration."""

    # API Key authentication
    enabled: bool = True
    api_keys: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Rate limiting
    rate_limit_enabled: bool = True
    requests_per_minute: int = 100
    requests_per_hour: int = 1000

    # Session management
    session_timeout_minutes: int = 60
    max_concurrent_sessions: int = 10

    # Security headers
    security_headers_enabled: bool = True


class APIKeyManager:
    """Manage API keys and authentication."""

    def __init__(self, config: AuthConfig, config_file: Path | None = None):
        """Initialize API key manager.

        Args:
            config: Authentication configuration
            config_file: Optional path to persistent key storage
        """
        self.config = config
        self.config_file = config_file
        self.api_keys: dict[str, dict[str, Any]] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load API keys from configuration."""
        if self.config.api_keys:
            self.api_keys.update(self.config.api_keys)

        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    stored_keys = json.load(f)
                    self.api_keys.update(stored_keys)
            except Exception:
                # If file is corrupted, continue with config keys only
                pass

    def _save_keys(self) -> None:
        """Save API keys to persistent storage with restricted permissions."""
        if not self.config_file:
            return

        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.api_keys, f, indent=2, default=str)
            # Restrict file permissions to owner only (0o600)
            os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            # Fail silently - don't break functionality if we can't persist
            pass

    def generate_api_key(
        self,
        name: str,
        permissions: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> str:
        """Generate a new API key.

        Args:
            name: Human-readable name for the key
            permissions: Optional permissions dict
            expires_at: Optional expiration datetime

        Returns:
            Generated API key string
        """
        # Generate secure random key
        api_key = f"cc_{secrets.token_urlsafe(32)}"

        key_info = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "permissions": permissions or {"read": True, "write": True},
            "usage_count": 0,
            "last_used": None,
        }

        self.api_keys[api_key] = key_info
        self._save_keys()

        return api_key

    def validate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Validate an API key and return key info if valid.

        Args:
            api_key: API key to validate

        Returns:
            Key info dict if valid, None otherwise
        """
        if not api_key or api_key not in self.api_keys:
            return None

        key_info = self.api_keys[api_key]

        # Check expiration
        if key_info.get("expires_at"):
            expires_at = datetime.fromisoformat(key_info["expires_at"])
            if datetime.now() > expires_at:
                return None

        # Update usage stats
        key_info["usage_count"] += 1
        key_info["last_used"] = datetime.now().isoformat()
        self._save_keys()

        return key_info

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key.

        Args:
            api_key: API key to revoke

        Returns:
            True if key was found and revoked
        """
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            self._save_keys()
            return True
        return False

    def list_api_keys(self) -> dict[str, dict[str, Any]]:
        """List all API keys with their info (excluding actual key values)."""
        return {
            key: {**info, "key_preview": f"{key[:8]}...{key[-4:]}"}
            for key, info in self.api_keys.items()
        }


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, config: AuthConfig):
        """Initialize rate limiter.

        Args:
            config: Authentication configuration
        """
        self.config = config
        self.requests: dict[str, list] = {}

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for given identifier.

        Args:
            identifier: Client identifier (API key, IP, etc.)

        Returns:
            True if request is allowed
        """
        if not self.config.rate_limit_enabled:
            return True

        now = time.time()

        # Clean old requests for this identifier
        if identifier not in self.requests:
            self.requests[identifier] = []

        # Remove requests older than 1 hour
        cutoff_hour = now - 3600
        cutoff_minute = now - 60

        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] if req_time > cutoff_hour
        ]

        # Count recent requests
        minute_requests = sum(
            1 for req_time in self.requests[identifier] if req_time > cutoff_minute
        )
        hour_requests = len(self.requests[identifier])

        # Check limits
        if minute_requests >= self.config.requests_per_minute:
            return False
        if hour_requests >= self.config.requests_per_hour:
            return False

        # Record this request
        self.requests[identifier].append(now)
        return True


class MCPAuthenticator:
    """Main authentication system for MCP server."""

    def __init__(self, config: AuthConfig, config_file: Path | None = None):
        """Initialize authenticator.

        Args:
            config: Authentication configuration
            config_file: Optional path to persistent storage
        """
        self.config = config
        self.api_key_manager = APIKeyManager(config, config_file)
        self.rate_limiter = RateLimiter(config)
        self.security = HTTPBearer(auto_error=False)

    async def authenticate_request(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(
            HTTPBearer(auto_error=False)
        ),
    ) -> dict[str, Any]:
        """Authenticate a request.

        Args:
            request: FastAPI request object
            credentials: HTTP Bearer credentials

        Returns:
            Authentication context with user info

        Raises:
            HTTPException: If authentication fails
        """
        if not self.config.enabled:
            return {"authenticated": False, "bypass": True}

        # Extract API key from Bearer token or X-API-Key header
        api_key = None
        if credentials and credentials.credentials:
            api_key = credentials.credentials

        # Also check for API key in X-API-Key header
        if not api_key:
            api_key = request.headers.get("X-API-Key")

        # NOTE: Query parameter auth (api_key=...) is deprecated and no longer supported
        # to prevent credential logging via URL parameters, proxy logs, and browser history

        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key required. Provide via Authorization header (Bearer token) or X-API-Key header.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate API key
        key_info = self.api_key_manager.validate_api_key(api_key)
        if not key_info:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Rate limiting
        client_ip = request.client.host if request.client else "unknown"
        rate_limit_id = f"{api_key}:{client_ip}"

        if not self.rate_limiter.is_allowed(rate_limit_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down your requests.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        return {
            "authenticated": True,
            "api_key": api_key,
            "key_info": key_info,
            "client_ip": client_ip,
        }

    def create_admin_key(self) -> str:
        """Create an admin API key for initial setup.

        Returns:
            Admin API key
        """
        return self.api_key_manager.generate_api_key(
            name="admin", permissions={"read": True, "write": True, "admin": True}
        )


def add_security_headers(response):
    """Add security headers to response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
