"""Tests for token estimation utilities."""

import pytest

from utils.tokens import estimate_tokens, format_tokens


class TestEstimateTokens:
    """Tests for token estimation."""

    def test_estimate_tokens_nonempty(self):
        """Test token estimation for non-empty string."""
        result = estimate_tokens("Hello world")
        assert result > 0

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty string."""
        assert estimate_tokens("") >= 0

    def test_estimate_tokens_short_text(self):
        """Test token estimation for short text."""
        # "Hello" = 5 chars, should be ~1 token (5/4 = 1.25, max(1, ...) = 1)
        result = estimate_tokens("Hello")
        assert result >= 1

    def test_estimate_tokens_long_text(self):
        """Test token estimation for long text."""
        text = "word " * 1000
        tokens = estimate_tokens(text)
        # Should be roughly 1000-1500 tokens
        # 5000 chars / 4 = 1250 tokens
        assert 500 < tokens < 2000

    def test_estimate_tokens_proportional(self):
        """Test that token count is roughly proportional to text length."""
        short_text = "hello world"
        long_text = short_text * 10

        short_tokens = estimate_tokens(short_text)
        long_tokens = estimate_tokens(long_text)

        # Long text should have roughly 10x tokens
        assert long_tokens > short_tokens
        assert 5 < long_tokens / short_tokens < 15

    def test_estimate_tokens_minimum_one(self):
        """Test that single character returns at least 1 token."""
        assert estimate_tokens("x") >= 1


class TestFormatTokens:
    """Tests for token formatting."""

    def test_format_tokens_small(self):
        """Test formatting of small token counts."""
        assert format_tokens(500) == "500"
        assert format_tokens(999) == "999"

    def test_format_tokens_thousands(self):
        """Test formatting of token counts in thousands."""
        assert format_tokens(1500) == "1.5k"
        assert format_tokens(10000) == "10.0k"
        assert format_tokens(1000) == "1.0k"

    def test_format_tokens_zero(self):
        """Test formatting of zero tokens."""
        assert format_tokens(0) == "0"

    def test_format_tokens_one(self):
        """Test formatting of single token."""
        assert format_tokens(1) == "1"

    def test_format_tokens_large(self):
        """Test formatting of large token counts."""
        assert format_tokens(100000) == "100.0k"
        assert format_tokens(1234567) == "1234.6k"

    def test_format_tokens_precision(self):
        """Test that formatting maintains consistent precision."""
        # Should always show one decimal place for thousands
        formatted = format_tokens(2345)
        assert "." in formatted or formatted.endswith("k")
        # Should be "2.3k"
        assert formatted == "2.3k"


class TestTokenIntegration:
    """Integration tests for token estimation and formatting."""

    def test_estimate_and_format_roundtrip(self):
        """Test estimating tokens and formatting result."""
        text = "This is a test message"
        tokens = estimate_tokens(text)
        formatted = format_tokens(tokens)
        # Should successfully format the estimated token count
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_long_document_estimation(self):
        """Test token estimation on a long document."""
        # Simulate a longer document
        paragraphs = [
            "This is paragraph one. It contains multiple sentences."
            "This is paragraph two. It also contains multiple sentences."
        ] * 100

        document = " ".join(paragraphs)
        tokens = estimate_tokens(document)

        # Should estimate a reasonable number of tokens
        assert tokens > 1000
        assert tokens < 100000

    def test_format_all_ranges(self):
        """Test formatting across all magnitude ranges."""
        test_values = [0, 1, 10, 100, 500, 999, 1000, 1500, 10000, 100000]
        for value in test_values:
            result = format_tokens(value)
            assert isinstance(result, str)
            assert len(result) > 0
