"""Security middleware for rate limiting and authentication."""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10  # Max requests in a 1-second window
    enabled: bool = True


@dataclass
class AuthConfig:
    """Configuration for API authentication."""

    enabled: bool = False
    api_keys: list[str] = field(default_factory=list)
    # If True, hash the keys before comparing (keys in config should be hashed)
    keys_are_hashed: bool = False


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        # Track requests per client: {client_id: [(timestamp, count), ...]}
        self._minute_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._hour_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._second_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Use X-Forwarded-For if behind a proxy, otherwise use client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _clean_old_entries(
        self,
        entries: list[tuple[float, int]],
        window_seconds: float,
        now: float,
    ) -> list[tuple[float, int]]:
        """Remove entries older than the window."""
        cutoff = now - window_seconds
        return [(ts, count) for ts, count in entries if ts > cutoff]

    def _count_requests(self, entries: list[tuple[float, int]]) -> int:
        """Count total requests in entries."""
        return sum(count for _, count in entries)

    def check_rate_limit(self, request: Request) -> None:
        """Check if request should be rate limited. Raises HTTPException if limited."""
        if not self.config.enabled:
            return

        client_id = self._get_client_id(request)
        now = time.time()

        # Check burst limit (per second)
        self._second_windows[client_id] = self._clean_old_entries(
            self._second_windows[client_id], 1.0, now
        )
        if self._count_requests(self._second_windows[client_id]) >= self.config.burst_limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Too many requests per second.",
                headers={"Retry-After": "1"},
            )

        # Check per-minute limit
        self._minute_windows[client_id] = self._clean_old_entries(
            self._minute_windows[client_id], 60.0, now
        )
        if self._count_requests(self._minute_windows[client_id]) >= self.config.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Too many requests per minute.",
                headers={"Retry-After": "60"},
            )

        # Check per-hour limit
        self._hour_windows[client_id] = self._clean_old_entries(
            self._hour_windows[client_id], 3600.0, now
        )
        if self._count_requests(self._hour_windows[client_id]) >= self.config.requests_per_hour:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Too many requests per hour.",
                headers={"Retry-After": "3600"},
            )

        # Record this request
        self._second_windows[client_id].append((now, 1))
        self._minute_windows[client_id].append((now, 1))
        self._hour_windows[client_id].append((now, 1))

    def get_remaining(self, request: Request) -> dict[str, int]:
        """Get remaining requests for a client."""
        if not self.config.enabled:
            return {"minute": -1, "hour": -1, "burst": -1}

        client_id = self._get_client_id(request)
        now = time.time()

        # Clean and count
        self._second_windows[client_id] = self._clean_old_entries(
            self._second_windows[client_id], 1.0, now
        )
        self._minute_windows[client_id] = self._clean_old_entries(
            self._minute_windows[client_id], 60.0, now
        )
        self._hour_windows[client_id] = self._clean_old_entries(
            self._hour_windows[client_id], 3600.0, now
        )

        return {
            "burst": max(
                0, self.config.burst_limit - self._count_requests(self._second_windows[client_id])
            ),
            "minute": max(
                0,
                self.config.requests_per_minute
                - self._count_requests(self._minute_windows[client_id]),
            ),
            "hour": max(
                0,
                self.config.requests_per_hour - self._count_requests(self._hour_windows[client_id]),
            ),
        }


# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """API Key authentication handler."""

    def __init__(self, config: AuthConfig | None = None) -> None:
        self.config = config or AuthConfig()

    def _hash_key(self, key: str) -> str:
        """Hash an API key for secure comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _verify_key(self, provided_key: str) -> bool:
        """Verify if the provided key is valid."""
        if not self.config.api_keys:
            return False

        if self.config.keys_are_hashed:
            hashed_provided = self._hash_key(provided_key)
            return any(
                secrets.compare_digest(hashed_provided, stored_key)
                for stored_key in self.config.api_keys
            )
        else:
            return any(
                secrets.compare_digest(provided_key, stored_key)
                for stored_key in self.config.api_keys
            )

    def verify(self, api_key: str | None) -> None:
        """Verify API key. Raises HTTPException if invalid."""
        if not self.config.enabled:
            return

        if api_key is None:
            raise HTTPException(
                status_code=401,
                detail="API key required. Provide X-API-Key header.",
            )

        if not self._verify_key(api_key):
            raise HTTPException(
                status_code=403,
                detail="Invalid API key.",
            )

    @staticmethod
    def generate_key() -> str:
        """Generate a new API key."""
        return secrets.token_urlsafe(32)

    def hash_key(self, key: str) -> str:
        """Hash a key for storage in config."""
        return self._hash_key(key)


def create_auth_dependency(
    auth: APIKeyAuth,
) -> Callable[[str | None], None]:
    """Create a FastAPI dependency for API key authentication."""

    def verify_api_key(api_key: str | None = Security(api_key_header)) -> None:
        auth.verify(api_key)

    return verify_api_key


def create_rate_limit_dependency(
    limiter: RateLimiter,
) -> Callable[[Request], None]:
    """Create a FastAPI dependency for rate limiting."""

    def check_rate_limit(request: Request) -> None:
        limiter.check_rate_limit(request)

    return check_rate_limit
