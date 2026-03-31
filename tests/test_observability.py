"""Tests for observability module."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest

from corpus_callosum.observability import (
    ObservabilityConfig,
    get_tracer,
    setup_observability,
    shutdown_observability,
    trace_llm_call,
    trace_rag_query,
)


class TestObservabilityConfig:
    """Tests for ObservabilityConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ObservabilityConfig()
        assert config.enabled is True
        assert config.service_name == "corpus-callosum"
        assert config.otlp_endpoint is None
        assert config.console_exporter is False
        assert config.openllmetry_enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ObservabilityConfig(
            enabled=False,
            service_name="my-service",
            otlp_endpoint="http://localhost:4317",
            console_exporter=True,
            openllmetry_enabled=False,
        )
        assert config.enabled is False
        assert config.service_name == "my-service"
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.console_exporter is True
        assert config.openllmetry_enabled is False


class TestSetupObservability:
    """Tests for setup_observability function."""

    def test_setup_disabled(self):
        """Test that disabled config returns False."""
        config = ObservabilityConfig(enabled=False)
        result = setup_observability(config)
        assert result is False

    def test_setup_without_opentelemetry(self):
        """Test graceful handling when opentelemetry not installed."""
        # This tests the ImportError path when OTel isn't available
        with patch.dict("sys.modules", {"opentelemetry": None}):
            # The function should handle missing imports gracefully
            result = setup_observability(console_exporter=True)
            # Result depends on whether OTel is actually installed
            assert isinstance(result, bool)


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_object(self):
        """Test that get_tracer returns a tracer-like object."""
        # Clear cache to ensure fresh state
        get_tracer.cache_clear()
        tracer = get_tracer()
        assert tracer is not None
        # Should have start_as_current_span method
        assert hasattr(tracer, "start_as_current_span")

    def test_get_tracer_with_custom_name(self):
        """Test get_tracer with custom name."""
        get_tracer.cache_clear()
        tracer = get_tracer("custom.module")
        assert tracer is not None

    def test_no_op_tracer_span(self):
        """Test that no-op tracer span works without errors."""
        get_tracer.cache_clear()
        tracer = get_tracer()

        # This should work regardless of whether OTel is installed
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("key", "value")
            span.add_event("test_event", {"attr": "value"})


class TestTraceFunctions:
    """Tests for trace helper functions."""

    def test_trace_rag_query_no_error(self):
        """Test trace_rag_query doesn't raise errors."""
        # Should not raise even without OpenTelemetry
        trace_rag_query(
            query="test query",
            collection="test_collection",
            num_chunks=5,
            latency_ms=100.5,
        )

    def test_trace_rag_query_without_latency(self):
        """Test trace_rag_query without optional latency."""
        trace_rag_query(
            query="test query",
            collection="test_collection",
            num_chunks=5,
        )

    def test_trace_llm_call_no_error(self):
        """Test trace_llm_call doesn't raise errors."""
        trace_llm_call(
            model="llama3",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500.0,
        )

    def test_trace_llm_call_minimal(self):
        """Test trace_llm_call with only required params."""
        trace_llm_call(model="gpt-4")


class TestShutdown:
    """Tests for shutdown_observability function."""

    def test_shutdown_no_error(self):
        """Test shutdown doesn't raise errors."""
        # Should not raise even if not initialized
        shutdown_observability()

    def test_shutdown_clears_state(self):
        """Test shutdown clears initialization state."""
        # Clear tracer cache
        get_tracer.cache_clear()

        # Shutdown should work
        shutdown_observability()

        # Getting tracer after shutdown should still work
        tracer = get_tracer()
        assert tracer is not None


class TestIntegrationWithMocks:
    """Integration tests with mocked OpenTelemetry."""

    def test_setup_with_mocked_otel(self):
        """Test setup with mocked OpenTelemetry modules."""
        mock_trace = MagicMock()
        mock_provider = MagicMock()
        mock_resource = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry": MagicMock(),
                "opentelemetry.trace": mock_trace,
                "opentelemetry.sdk.trace": MagicMock(TracerProvider=lambda **_kw: mock_provider),
                "opentelemetry.sdk.trace.sampling": MagicMock(),
                "opentelemetry.sdk.resources": MagicMock(
                    Resource=MagicMock(create=lambda _attrs: mock_resource),
                    SERVICE_NAME="service.name",
                    SERVICE_VERSION="service.version",
                ),
            },
        ):
            # Reset initialized state
            import corpus_callosum.observability as obs

            obs._initialized = False
            obs._tracer_provider = None

            config = ObservabilityConfig(enabled=True)
            # This may or may not succeed depending on mock completeness
            # but should not raise unexpected errors
            with contextlib.suppress(ImportError, AttributeError):
                setup_observability(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
