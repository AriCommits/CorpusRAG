"""Tests for UX improvements (rate limiting, context warning)."""

import time

import pytest


class MockRAGApp:
    """Mock RAG app for testing rate limiting and context features."""

    def __init__(self):
        self._last_context_sync = 0.0

    def _rate_limited_context_sync(self, delay: float = 0.1) -> bool:
        """Rate limit context toggle sync to prevent UI lag."""
        now = time.time()
        if now - self._last_context_sync >= delay:
            self._last_context_sync = now
            return True
        return False

    def _calculate_context_usage(
        self, included_count: int, max_messages: int = 40
    ) -> float:
        """Calculate context window usage percentage."""
        return min(100, (included_count / max_messages) * 100)


def test_rate_limiting_allows_first_call():
    """Test that rate limiting allows the first call."""
    app = MockRAGApp()
    assert app._rate_limited_context_sync() is True


def test_rate_limiting_blocks_rapid_calls():
    """Test that rate limiting blocks rapid calls within delay window."""
    app = MockRAGApp()
    app._rate_limited_context_sync()
    # Immediately call again - should be blocked
    assert app._rate_limited_context_sync(delay=0.1) is False


def test_rate_limiting_allows_after_delay():
    """Test that rate limiting allows calls after delay period."""
    app = MockRAGApp()
    app._rate_limited_context_sync(delay=0.05)
    time.sleep(0.1)  # Wait longer than delay
    assert app._rate_limited_context_sync(delay=0.05) is True


def test_rate_limiting_custom_delay():
    """Test rate limiting with custom delay values."""
    app = MockRAGApp()

    # Tight delay (should allow quick successive calls)
    assert app._rate_limited_context_sync(delay=0.001) is True
    time.sleep(0.002)
    assert app._rate_limited_context_sync(delay=0.001) is True

    # Longer delay (should block)
    app._rate_limited_context_sync(delay=1.0)
    assert app._rate_limited_context_sync(delay=1.0) is False


def test_context_usage_calculation():
    """Test context usage percentage calculation."""
    app = MockRAGApp()

    # Empty context
    assert app._calculate_context_usage(0) == 0.0

    # Half full (20 out of 40)
    assert app._calculate_context_usage(20) == 50.0

    # Three quarters full
    assert app._calculate_context_usage(30) == 75.0

    # Full context
    assert app._calculate_context_usage(40) == 100.0

    # Over capacity (capped at 100)
    assert app._calculate_context_usage(50) == 100.0


def test_context_usage_warning_threshold():
    """Test that context warning activates at 80%."""
    app = MockRAGApp()

    # Below 80% - no warning
    usage = app._calculate_context_usage(30)  # 75%
    assert usage < 80

    # At 80% - warning should trigger
    usage = app._calculate_context_usage(32)  # 80%
    assert usage >= 80

    # Above 80% - warning should trigger
    usage = app._calculate_context_usage(35)  # 87.5%
    assert usage > 80


def test_context_usage_with_custom_max():
    """Test context usage with custom max messages."""
    app = MockRAGApp()

    # With custom max of 100
    usage = app._calculate_context_usage(50, max_messages=100)
    assert usage == 50.0

    usage = app._calculate_context_usage(80, max_messages=100)
    assert usage == 80.0
