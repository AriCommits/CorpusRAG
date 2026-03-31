"""Tests for security module - rate limiting and API key authentication."""

from __future__ import annotations

import hashlib
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from corpus_callosum.security import (
    APIKeyAuth,
    AuthConfig,
    RateLimitConfig,
    RateLimiter,
    create_auth_dependency,
    create_rate_limit_dependency,
)


def make_mock_request(client_host: str = "127.0.0.1", forwarded_for: str | None = None) -> MagicMock:
    """Create a mock FastAPI Request object."""
    request = MagicMock()
    request.client.host = client_host
    if forwarded_for:
        request.headers.get.return_value = forwarded_for
    else:
        request.headers.get.return_value = None
    return request


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_limit == 10
        assert config.enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            burst_limit=5,
            enabled=False,
        )
        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500
        assert config.burst_limit == 5
        assert config.enabled is False


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_disabled(self):
        """Test that disabled rate limiter allows all requests."""
        config = RateLimitConfig(enabled=False)
        limiter = RateLimiter(config)
        request = make_mock_request()

        # Should not raise for any number of requests
        for _ in range(100):
            limiter.check_rate_limit(request)

    def test_burst_limit_exceeded(self):
        """Test that burst limit raises HTTPException."""
        config = RateLimitConfig(burst_limit=3, enabled=True)
        limiter = RateLimiter(config)
        request = make_mock_request()

        # First 3 requests should pass
        for _ in range(3):
            limiter.check_rate_limit(request)

        # 4th request should fail
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.status_code == 429
        assert "per second" in exc_info.value.detail

    def test_per_minute_limit_exceeded(self):
        """Test that per-minute limit raises HTTPException."""
        config = RateLimitConfig(
            burst_limit=100,  # High burst to not trigger it
            requests_per_minute=5,
            enabled=True,
        )
        limiter = RateLimiter(config)
        request = make_mock_request()

        # First 5 requests should pass
        for _ in range(5):
            limiter.check_rate_limit(request)

        # 6th request should fail
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.status_code == 429
        assert "per minute" in exc_info.value.detail

    def test_per_hour_limit_exceeded(self):
        """Test that per-hour limit raises HTTPException."""
        config = RateLimitConfig(
            burst_limit=100,
            requests_per_minute=100,
            requests_per_hour=5,
            enabled=True,
        )
        limiter = RateLimiter(config)
        request = make_mock_request()

        # First 5 requests should pass
        for _ in range(5):
            limiter.check_rate_limit(request)

        # 6th request should fail
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.status_code == 429
        assert "per hour" in exc_info.value.detail

    def test_client_id_from_forwarded_header(self):
        """Test that X-Forwarded-For header is used for client ID."""
        config = RateLimitConfig(burst_limit=2, enabled=True)
        limiter = RateLimiter(config)

        # Two different clients behind proxy
        request1 = make_mock_request(forwarded_for="192.168.1.1, 10.0.0.1")
        request2 = make_mock_request(forwarded_for="192.168.1.2, 10.0.0.1")

        # Each client should have their own limit
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request2)
        limiter.check_rate_limit(request2)

        # Both should now be at limit
        with pytest.raises(HTTPException):
            limiter.check_rate_limit(request1)
        with pytest.raises(HTTPException):
            limiter.check_rate_limit(request2)

    def test_get_remaining_disabled(self):
        """Test get_remaining returns -1 when disabled."""
        config = RateLimitConfig(enabled=False)
        limiter = RateLimiter(config)
        request = make_mock_request()

        remaining = limiter.get_remaining(request)
        assert remaining == {"minute": -1, "hour": -1, "burst": -1}

    def test_get_remaining_tracks_usage(self):
        """Test get_remaining accurately tracks usage."""
        config = RateLimitConfig(
            burst_limit=10,
            requests_per_minute=20,
            requests_per_hour=100,
            enabled=True,
        )
        limiter = RateLimiter(config)
        request = make_mock_request()

        # Check initial remaining
        remaining = limiter.get_remaining(request)
        assert remaining["burst"] == 10
        assert remaining["minute"] == 20
        assert remaining["hour"] == 100

        # Make 3 requests
        for _ in range(3):
            limiter.check_rate_limit(request)

        # Check remaining after requests
        remaining = limiter.get_remaining(request)
        assert remaining["burst"] == 7
        assert remaining["minute"] == 17
        assert remaining["hour"] == 97


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AuthConfig()
        assert config.enabled is False
        assert config.api_keys == []
        assert config.keys_are_hashed is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AuthConfig(
            enabled=True,
            api_keys=["key1", "key2"],
            keys_are_hashed=True,
        )
        assert config.enabled is True
        assert config.api_keys == ["key1", "key2"]
        assert config.keys_are_hashed is True


class TestAPIKeyAuth:
    """Tests for APIKeyAuth class."""

    def test_auth_disabled_allows_all(self):
        """Test that disabled auth allows any request."""
        config = AuthConfig(enabled=False)
        auth = APIKeyAuth(config)

        # Should not raise for any key
        auth.verify(None)
        auth.verify("any-key")
        auth.verify("")

    def test_auth_requires_key(self):
        """Test that enabled auth requires a key."""
        config = AuthConfig(enabled=True, api_keys=["valid-key"])
        auth = APIKeyAuth(config)

        with pytest.raises(HTTPException) as exc_info:
            auth.verify(None)

        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    def test_auth_rejects_invalid_key(self):
        """Test that invalid key is rejected."""
        config = AuthConfig(enabled=True, api_keys=["valid-key"])
        auth = APIKeyAuth(config)

        with pytest.raises(HTTPException) as exc_info:
            auth.verify("invalid-key")

        assert exc_info.value.status_code == 403
        assert "Invalid API key" in exc_info.value.detail

    def test_auth_accepts_valid_key(self):
        """Test that valid key is accepted."""
        config = AuthConfig(enabled=True, api_keys=["valid-key-123"])
        auth = APIKeyAuth(config)

        # Should not raise
        auth.verify("valid-key-123")

    def test_auth_accepts_multiple_keys(self):
        """Test that any of multiple valid keys is accepted."""
        config = AuthConfig(enabled=True, api_keys=["key1", "key2", "key3"])
        auth = APIKeyAuth(config)

        # All should be valid
        auth.verify("key1")
        auth.verify("key2")
        auth.verify("key3")

    def test_auth_with_hashed_keys(self):
        """Test authentication with hashed keys."""
        raw_key = "my-secret-api-key"
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

        config = AuthConfig(enabled=True, api_keys=[hashed_key], keys_are_hashed=True)
        auth = APIKeyAuth(config)

        # Raw key should work (gets hashed for comparison)
        auth.verify(raw_key)

        # Wrong key should fail
        with pytest.raises(HTTPException) as exc_info:
            auth.verify("wrong-key")
        assert exc_info.value.status_code == 403

    def test_generate_key(self):
        """Test API key generation."""
        key1 = APIKeyAuth.generate_key()
        key2 = APIKeyAuth.generate_key()

        # Keys should be unique
        assert key1 != key2
        # Keys should be non-empty strings
        assert isinstance(key1, str)
        assert len(key1) > 20  # Should be reasonably long

    def test_hash_key(self):
        """Test API key hashing."""
        auth = APIKeyAuth()
        key = "test-key"
        hashed = auth.hash_key(key)

        # Should be SHA-256 hex digest
        assert len(hashed) == 64
        assert hashed == hashlib.sha256(key.encode()).hexdigest()

    def test_empty_api_keys_rejects_all(self):
        """Test that empty api_keys list rejects all keys."""
        config = AuthConfig(enabled=True, api_keys=[])
        auth = APIKeyAuth(config)

        with pytest.raises(HTTPException) as exc_info:
            auth.verify("any-key")
        assert exc_info.value.status_code == 403


class TestDependencyFactories:
    """Tests for dependency factory functions."""

    def test_create_auth_dependency(self):
        """Test create_auth_dependency returns callable."""
        config = AuthConfig(enabled=True, api_keys=["test-key"])
        auth = APIKeyAuth(config)
        dependency = create_auth_dependency(auth)

        # Should be callable
        assert callable(dependency)

        # Should pass with valid key
        dependency("test-key")

        # Should raise with invalid key
        with pytest.raises(HTTPException):
            dependency("wrong-key")

    def test_create_rate_limit_dependency(self):
        """Test create_rate_limit_dependency returns callable."""
        config = RateLimitConfig(burst_limit=2, enabled=True)
        limiter = RateLimiter(config)
        dependency = create_rate_limit_dependency(limiter)
        request = make_mock_request()

        # Should be callable
        assert callable(dependency)

        # Should pass initially
        dependency(request)
        dependency(request)

        # Should raise when limit exceeded
        with pytest.raises(HTTPException):
            dependency(request)


class TestTimingBehavior:
    """Tests for time-based rate limit behavior."""

    def test_burst_window_resets(self):
        """Test that burst window resets after 1 second."""
        config = RateLimitConfig(
            burst_limit=2,
            requests_per_minute=100,
            requests_per_hour=1000,
            enabled=True,
        )
        limiter = RateLimiter(config)
        request = make_mock_request()

        # Use up burst limit
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)

        with pytest.raises(HTTPException):
            limiter.check_rate_limit(request)

        # Wait for window to reset
        time.sleep(1.1)

        # Should work again
        limiter.check_rate_limit(request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
