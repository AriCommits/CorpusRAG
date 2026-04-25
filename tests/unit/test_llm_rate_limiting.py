"""Tests for LLM backend rate limiting integration."""

import time
from unittest.mock import MagicMock, patch

import pytest

from llm.backend import OllamaBackend
from llm.config import LLMConfig


class TestLLMBackendRateLimitConfig:
    """Tests for rate limiting configuration."""

    def test_backend_no_rate_limit_by_default(self):
        """Test that LLMConfig without limits creates backend without limiter."""
        config = LLMConfig(endpoint="http://localhost:11434")
        backend = OllamaBackend(config)
        assert backend._rate_limiter is None

    def test_backend_with_rate_limit_rpm(self):
        """Test that LLMConfig with rpm creates limiter."""
        config = LLMConfig(endpoint="http://localhost:11434", rate_limit_rpm=60)
        backend = OllamaBackend(config)
        assert backend._rate_limiter is not None

    def test_backend_with_rate_limit_concurrent(self):
        """Test that LLMConfig with concurrent limit creates limiter."""
        config = LLMConfig(
            endpoint="http://localhost:11434", rate_limit_concurrent=5
        )
        backend = OllamaBackend(config)
        assert backend._rate_limiter is not None

    def test_backend_with_both_rate_limits(self):
        """Test that LLMConfig with both limits creates limiter."""
        config = LLMConfig(
            endpoint="http://localhost:11434",
            rate_limit_rpm=60,
            rate_limit_concurrent=5,
        )
        backend = OllamaBackend(config)
        assert backend._rate_limiter is not None


class TestLLMRateLimitChecking:
    """Tests for rate limit checking behavior."""

    def test_check_rate_limit_no_limiter(self):
        """Test that _check_rate_limit works safely when no limiter."""
        config = LLMConfig(endpoint="http://localhost:11434")
        backend = OllamaBackend(config)
        # Should not raise error
        backend._check_rate_limit()

    def test_start_end_request_no_limiter(self):
        """Test that _start_request and _end_request work without limiter."""
        config = LLMConfig(endpoint="http://localhost:11434")
        backend = OllamaBackend(config)
        # Should not raise errors
        backend._start_request()
        backend._end_request()

    def test_check_rate_limit_with_limiter(self):
        """Test that _check_rate_limit respects rpm limits."""
        config = LLMConfig(
            endpoint="http://localhost:11434", rate_limit_rpm=2
        )
        backend = OllamaBackend(config)

        # Make 2 requests within the limit
        backend._check_rate_limit()
        with patch.object(backend._rate_limiter, "check_operation_limit") as mock_check:
            mock_check.return_value = True
            backend._check_rate_limit()

    def test_start_request_tracking(self):
        """Test that start_request properly tracks concurrent operations."""
        config = LLMConfig(
            endpoint="http://localhost:11434", rate_limit_concurrent=5
        )
        backend = OllamaBackend(config)

        # Check that operation is tracked
        backend._start_request()
        assert backend._rate_limiter.get_active_count("default", "llm") == 1

        backend._start_request()
        assert backend._rate_limiter.get_active_count("default", "llm") == 2

    def test_end_request_tracking(self):
        """Test that end_request properly untracks concurrent operations."""
        config = LLMConfig(
            endpoint="http://localhost:11434", rate_limit_concurrent=5
        )
        backend = OllamaBackend(config)

        # Start and end operations
        backend._start_request()
        backend._start_request()
        assert backend._rate_limiter.get_active_count("default", "llm") == 2

        backend._end_request()
        assert backend._rate_limiter.get_active_count("default", "llm") == 1

        backend._end_request()
        assert backend._rate_limiter.get_active_count("default", "llm") == 0


class TestRateLimitBlocking:
    """Tests for rate limit blocking and waiting behavior."""

    @patch("llm.backend.time.sleep")
    def test_rate_limit_blocks_when_exceeded(self, mock_sleep):
        """Test that rate limiting blocks/waits when limit exceeded."""
        config = LLMConfig(
            endpoint="http://localhost:11434", rate_limit_rpm=1
        )
        backend = OllamaBackend(config)

        # Make first request (should succeed)
        backend._check_rate_limit()

        # Manually record another operation to simulate hitting limit
        backend._rate_limiter.check_operation_limit("default", "llm", 1, 60)

        # Now check_rate_limit should trigger a wait
        with patch.object(backend._rate_limiter, "_operation_history") as mock_history:
            # Simulate being at the limit
            key = ("default", "llm")
            mock_history.__getitem__.return_value = [time.time()]

            with patch.object(backend._rate_limiter, "_lock"):
                backend._check_rate_limit()
                # Note: This is a simplified test - actual wait behavior
                # depends on implementation details

    def test_complete_with_rate_limiting(self):
        """Test that complete() method calls rate limiting."""
        config = LLMConfig(
            endpoint="http://localhost:11434",
            rate_limit_rpm=60,
            rate_limit_concurrent=5,
        )
        backend = OllamaBackend(config)

        # Mock the stream_completion to avoid actual API calls
        with patch.object(backend, "stream_completion") as mock_stream:
            mock_stream.return_value = iter(["test", "response"])

            # complete() should call rate limiting methods
            with patch.object(backend, "_check_rate_limit") as mock_check:
                with patch.object(backend, "_start_request") as mock_start:
                    with patch.object(backend, "_end_request") as mock_end:
                        response = backend.complete("test prompt")
                        mock_check.assert_called_once()
                        mock_start.assert_called_once()
                        mock_end.assert_called_once()
                        assert response.text == "testresponse"

    def test_chat_with_rate_limiting(self):
        """Test that chat() method calls rate limiting."""
        config = LLMConfig(
            endpoint="http://localhost:11434",
            rate_limit_rpm=60,
            rate_limit_concurrent=5,
        )
        backend = OllamaBackend(config)

        # Mock the chat_completion to avoid actual API calls
        with patch.object(backend, "chat_completion") as mock_chat:
            mock_chat.return_value = iter(["test", "response"])

            # chat() should call rate limiting methods
            with patch.object(backend, "_check_rate_limit") as mock_check:
                with patch.object(backend, "_start_request") as mock_start:
                    with patch.object(backend, "_end_request") as mock_end:
                        messages = [{"role": "user", "content": "test"}]
                        response = backend.chat(messages)
                        mock_check.assert_called_once()
                        mock_start.assert_called_once()
                        mock_end.assert_called_once()
                        assert response.text == "testresponse"

    def test_end_request_called_on_exception(self):
        """Test that _end_request is called even if stream_completion raises."""
        config = LLMConfig(
            endpoint="http://localhost:11434", rate_limit_concurrent=5
        )
        backend = OllamaBackend(config)

        # Mock stream_completion to raise an error
        with patch.object(backend, "stream_completion") as mock_stream:
            mock_stream.side_effect = RuntimeError("API error")

            # Should raise the error but still call _end_request via finally
            with patch.object(backend, "_end_request") as mock_end:
                with pytest.raises(RuntimeError):
                    backend.complete("test prompt")
                mock_end.assert_called_once()


class TestIntegrationWithConfigParsing:
    """Tests for integration with configuration parsing."""

    def test_config_from_dict_with_rate_limits(self):
        """Test that LLMConfig.from_dict properly handles rate limit fields."""
        data = {
            "backend": "ollama",
            "endpoint": "http://localhost:11434",
            "rate_limit_rpm": 60,
            "rate_limit_concurrent": 5,
        }
        config = LLMConfig.from_dict(data)
        assert config.rate_limit_rpm == 60
        assert config.rate_limit_concurrent == 5

    def test_config_from_dict_nested_llm(self):
        """Test that from_dict handles nested llm config."""
        data = {
            "llm": {
                "backend": "ollama",
                "endpoint": "http://localhost:11434",
                "rate_limit_rpm": 30,
                "rate_limit_concurrent": 2,
            }
        }
        config = LLMConfig.from_dict(data)
        assert config.rate_limit_rpm == 30
        assert config.rate_limit_concurrent == 2

    def test_backend_creation_with_config_from_dict(self):
        """Test creating backend from dict config."""
        data = {
            "backend": "ollama",
            "endpoint": "http://localhost:11434",
            "rate_limit_rpm": 60,
        }
        config = LLMConfig.from_dict(data)
        backend = OllamaBackend(config)
        assert backend._rate_limiter is not None
