"""Tests for LLM backend abstraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from corpus_callosum.llm_backends import (
    LLMBackendType,
    LLMConfig,
    OllamaBackend,
    OpenAICompatibleBackend,
    AnthropicCompatibleBackend,
    create_backend,
)


class TestLLMConfig:
    """Tests for LLMConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LLMConfig()

        assert config.backend == LLMBackendType.OLLAMA
        assert config.endpoint == "http://localhost:11434"
        assert config.model is None  # Auto-detect by default
        assert config.timeout_seconds == 120.0
        assert config.api_key is None
        assert config.fallback_models == []

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LLMConfig(
            backend=LLMBackendType.OPENAI_COMPATIBLE,
            endpoint="http://example.com",
            model="gpt-4",
            timeout_seconds=60.0,
            api_key="test-key",
            fallback_models=["gpt-3.5-turbo"],
        )

        assert config.backend == LLMBackendType.OPENAI_COMPATIBLE
        assert config.endpoint == "http://example.com"
        assert config.model == "gpt-4"
        assert config.timeout_seconds == 60.0
        assert config.api_key == "test-key"
        assert config.fallback_models == ["gpt-3.5-turbo"]


class TestCreateBackend:
    """Tests for backend factory function."""

    def test_create_ollama_backend(self):
        """Test creating Ollama backend."""
        config = LLMConfig(backend=LLMBackendType.OLLAMA)
        backend = create_backend(config)

        assert isinstance(backend, OllamaBackend)

    def test_create_openai_backend(self):
        """Test creating OpenAI-compatible backend."""
        config = LLMConfig(backend=LLMBackendType.OPENAI_COMPATIBLE)
        backend = create_backend(config)

        assert isinstance(backend, OpenAICompatibleBackend)

    def test_create_anthropic_backend(self):
        """Test creating Anthropic-compatible backend."""
        config = LLMConfig(backend=LLMBackendType.ANTHROPIC_COMPATIBLE)
        backend = create_backend(config)

        assert isinstance(backend, AnthropicCompatibleBackend)

    def test_unknown_backend_raises(self):
        """Test that unknown backend type raises ValueError."""
        config = LLMConfig()
        # Manually set an invalid backend type
        object.__setattr__(config, "backend", "invalid")

        with pytest.raises(ValueError, match="Unknown backend type"):
            create_backend(config)


class TestOllamaBackend:
    """Tests for Ollama backend."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return LLMConfig(
            backend=LLMBackendType.OLLAMA,
            endpoint="http://localhost:11434",
            model="llama3.2",
        )

    @pytest.fixture
    def config_no_model(self):
        """Create a test config without model specified."""
        return LLMConfig(
            backend=LLMBackendType.OLLAMA,
            endpoint="http://localhost:11434",
            model="",  # Empty string = auto-detect
        )

    @pytest.fixture
    def backend(self, config):
        """Create an Ollama backend."""
        return OllamaBackend(config)

    @pytest.fixture
    def backend_no_model(self, config_no_model):
        """Create an Ollama backend without model."""
        return OllamaBackend(config_no_model)

    def test_stream_completion_uses_config_model(self, backend):
        """Test that stream_completion uses model from config."""
        mock_response_lines = [
            '{"response": "Hello", "done": false}',
            '{"response": "", "done": true}',
        ]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(backend.stream_completion("test prompt"))

            assert tokens == ["Hello"]
            # Verify the endpoint and payload
            call_args = mock_stream.call_args
            assert "http://localhost:11434/api/generate" in str(call_args)
            assert call_args.kwargs["json"]["model"] == "llama3.2"

    def test_stream_completion_uses_override_model(self, backend):
        """Test that stream_completion can override the model."""
        mock_response_lines = [
            '{"response": "Hi", "done": false}',
            '{"response": "", "done": true}',
        ]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(backend.stream_completion("test", model="mistral"))

            assert tokens == ["Hi"]
            call_args = mock_stream.call_args
            assert call_args.kwargs["json"]["model"] == "mistral"

    def test_auto_detect_model_success(self, backend_no_model):
        """Test auto-detection of Ollama model."""
        # Clear any cached model
        OllamaBackend._cached_default_model = None

        mock_tags_response = {
            "models": [
                {"name": "llama3.2:latest", "size": 2000000000},
                {"name": "mistral:latest", "size": 4000000000},
            ]
        }

        mock_stream_lines = [
            '{"response": "Auto", "done": false}',
            '{"response": "", "done": true}',
        ]

        with patch("httpx.get") as mock_get, patch("httpx.stream") as mock_stream:
            # Mock the tags endpoint
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = mock_tags_response
            mock_get_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_get_response

            # Mock the stream endpoint
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_stream_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(backend_no_model.stream_completion("test"))

            assert tokens == ["Auto"]
            # Verify it used the first model from the list
            call_args = mock_stream.call_args
            assert call_args.kwargs["json"]["model"] == "llama3.2:latest"

    def test_auto_detect_model_caches_result(self, backend_no_model):
        """Test that auto-detected model is cached."""
        # Clear cache first
        OllamaBackend._cached_default_model = None

        mock_tags_response = {"models": [{"name": "cached-model:latest"}]}

        mock_stream_lines = [
            '{"response": "OK", "done": true}',
        ]

        with patch("httpx.get") as mock_get, patch("httpx.stream") as mock_stream:
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = mock_tags_response
            mock_get_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_get_response

            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_stream_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            # First call - should query /api/tags
            list(backend_no_model.stream_completion("test1"))
            assert mock_get.call_count == 1

            # Reset stream mock for second call
            mock_response.iter_lines.return_value = iter(
                [
                    '{"response": "OK2", "done": true}',
                ]
            )

            # Second call - should use cached model, not query again
            list(backend_no_model.stream_completion("test2"))
            assert mock_get.call_count == 1  # Still 1, not 2

    def test_auto_detect_model_failure_raises(self, backend_no_model):
        """Test that auto-detection failure raises helpful error."""
        # Clear cache
        OllamaBackend._cached_default_model = None

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            with pytest.raises(ValueError, match="No model specified and auto-detection failed"):
                list(backend_no_model.stream_completion("test"))

    def test_auto_detect_model_empty_list_raises(self, backend_no_model):
        """Test that empty model list raises helpful error."""
        # Clear cache
        OllamaBackend._cached_default_model = None

        mock_tags_response = {"models": []}

        with patch("httpx.get") as mock_get:
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = mock_tags_response
            mock_get_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_get_response

            with pytest.raises(ValueError, match="No model specified and auto-detection failed"):
                list(backend_no_model.stream_completion("test"))

    def test_parse_line_valid_json(self, backend):
        """Test parsing valid JSON."""
        result = backend._parse_line('{"response": "test", "done": false}')
        assert result == {"response": "test", "done": False}

    def test_parse_line_with_data_prefix(self, backend):
        """Test parsing with data: prefix."""
        result = backend._parse_line('data: {"response": "test"}')
        assert result == {"response": "test"}

    def test_parse_line_done_marker(self, backend):
        """Test parsing [DONE] marker."""
        assert backend._parse_line("[DONE]") == {}
        assert backend._parse_line("data: [DONE]") == {}

    def test_parse_line_invalid_json(self, backend):
        """Test parsing invalid JSON returns empty dict."""
        assert backend._parse_line("not json") == {}
        assert backend._parse_line("") == {}

    def test_parse_line_non_dict_json(self, backend):
        """Test parsing non-dict JSON returns empty dict."""
        assert backend._parse_line('["array"]') == {}
        assert backend._parse_line('"string"') == {}


class TestOpenAICompatibleBackend:
    """Tests for OpenAI-compatible backend."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return LLMConfig(
            backend=LLMBackendType.OPENAI_COMPATIBLE,
            endpoint="http://localhost:8080",
            model="gpt-4",
            api_key="test-api-key",
        )

    @pytest.fixture
    def backend(self, config):
        """Create an OpenAI-compatible backend."""
        return OpenAICompatibleBackend(config)

    def test_stream_completion_converts_to_chat(self, backend):
        """Test that stream_completion wraps prompt in messages."""
        mock_response_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            "data: [DONE]",
        ]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(backend.stream_completion("test prompt"))

            assert tokens == ["Hello"]
            # Verify it uses chat completions endpoint
            call_args = mock_stream.call_args
            assert "/v1/chat/completions" in str(call_args)

    def test_includes_auth_header(self, backend):
        """Test that Authorization header is included."""
        mock_response_lines = ["data: [DONE]"]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            list(backend.stream_completion("test"))

            call_args = mock_stream.call_args
            headers = call_args.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test-api-key"


class TestAnthropicCompatibleBackend:
    """Tests for Anthropic-compatible backend."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return LLMConfig(
            backend=LLMBackendType.ANTHROPIC_COMPATIBLE,
            endpoint="http://localhost:8080",
            model="claude-3",
            api_key="test-anthropic-key",
        )

    @pytest.fixture
    def backend(self, config):
        """Create an Anthropic-compatible backend."""
        return AnthropicCompatibleBackend(config)

    def test_stream_completion_converts_to_messages(self, backend):
        """Test that stream_completion wraps prompt in messages."""
        mock_response_lines = [
            'data: {"type": "content_block_delta", "delta": {"text": "Hello"}}',
            'data: {"type": "message_stop"}',
        ]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(backend.stream_completion("test prompt"))

            assert tokens == ["Hello"]
            # Verify it uses messages endpoint
            call_args = mock_stream.call_args
            assert "/v1/messages" in str(call_args)

    def test_includes_anthropic_headers(self, backend):
        """Test that Anthropic-specific headers are included."""
        mock_response_lines = ['data: {"type": "message_stop"}']

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            list(backend.stream_completion("test"))

            call_args = mock_stream.call_args
            headers = call_args.kwargs.get("headers", {})
            assert headers.get("x-api-key") == "test-anthropic-key"
            assert headers.get("anthropic-version") == "2023-06-01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
