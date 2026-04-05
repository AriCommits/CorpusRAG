"""Observability module with OpenTelemetry and OpenLLMetry instrumentation.

This module provides:
- OpenTelemetry tracing for requests and operations
- OpenLLMetry for LLM-specific observability
- Custom metrics for RAG-specific measurements
- Span attributes for debugging and monitoring

Usage:
    from corpus_callosum.observability import setup_observability, get_tracer

    # Initialize at application startup
    setup_observability(service_name="corpus-callosum")

    # Get tracer for custom spans
    tracer = get_tracer()
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("custom.attribute", "value")
        # ... do work
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)


def _redact_url(url: str | None) -> str | None:
    """Redact credentials from a URL for safe logging."""
    if not url:
        return url
    try:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        if parsed.password:
            parsed = parsed._replace(netloc=f"{parsed.username}:***@{parsed.hostname}")
            return urlunparse(parsed)
        return url
    except Exception:
        return url


@dataclass
class ObservabilityConfig:
    """Configuration for observability setup."""

    enabled: bool = True
    service_name: str = "corpus-callosum"
    service_version: str = "0.1.0"

    # OTLP exporter settings
    otlp_endpoint: str | None = None  # e.g., "http://localhost:4317"
    otlp_headers: dict[str, str] | None = None

    # Console exporter for development
    console_exporter: bool = False

    # OpenLLMetry settings
    openllmetry_enabled: bool = True

    # Sampling
    sampling_ratio: float = 1.0  # 1.0 = trace everything


_tracer_provider: TracerProvider | None = None
_initialized: bool = False


def _get_resource(config: ObservabilityConfig) -> Any:
    """Create OpenTelemetry resource with service info."""
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

    return Resource.create(
        {
            SERVICE_NAME: config.service_name,
            SERVICE_VERSION: config.service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )


def _setup_tracer_provider(config: ObservabilityConfig) -> TracerProvider:
    """Set up the OpenTelemetry tracer provider."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    sampler = TraceIdRatioBased(config.sampling_ratio)
    resource = _get_resource(config)

    provider = TracerProvider(resource=resource, sampler=sampler)

    # Add exporters based on config
    if config.console_exporter:
        _add_console_exporter(provider)

    if config.otlp_endpoint:
        _add_otlp_exporter(provider, config)

    return provider


def _add_console_exporter(provider: TracerProvider) -> None:
    """Add console exporter for development/debugging."""
    try:
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        logger.info("Console span exporter enabled")
    except ImportError:
        logger.warning("Console exporter not available")


def _add_otlp_exporter(provider: TracerProvider, config: ObservabilityConfig) -> None:
    """Add OTLP exporter for production telemetry."""
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint,
            headers=config.otlp_headers,
        )
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        logger.info("OTLP exporter enabled: %s", _redact_url(config.otlp_endpoint))
    except ImportError:
        logger.warning(
            "OTLP exporter not available. Install with: pip install opentelemetry-exporter-otlp"
        )


def _setup_openllmetry() -> bool:
    """Initialize OpenLLMetry for LLM observability."""
    try:
        from openllmetry.sdk import init as openllmetry_init

        openllmetry_init()
        logger.info("OpenLLMetry instrumentation enabled")
        return True
    except ImportError:
        logger.debug("OpenLLMetry not available. Install with: pip install openllmetry")
        return False


def _instrument_fastapi() -> bool:
    """Instrument FastAPI for automatic tracing."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument()
        logger.info("FastAPI instrumentation enabled")
        return True
    except ImportError:
        logger.debug(
            "FastAPI instrumentation not available. "
            "Install with: pip install opentelemetry-instrumentation-fastapi"
        )
        return False


def _instrument_httpx() -> bool:
    """Instrument httpx for outbound request tracing."""
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
        return True
    except ImportError:
        logger.debug(
            "HTTPX instrumentation not available. "
            "Install with: pip install opentelemetry-instrumentation-httpx"
        )
        return False


def setup_observability(
    config: ObservabilityConfig | None = None,
    *,
    service_name: str | None = None,
    otlp_endpoint: str | None = None,
    console_exporter: bool | None = None,
) -> bool:
    """Initialize OpenTelemetry observability.

    Args:
        config: Full configuration object (optional)
        service_name: Override service name
        otlp_endpoint: OTLP collector endpoint
        console_exporter: Enable console output for debugging

    Returns:
        True if observability was successfully initialized

    Example:
        # Development mode with console output
        setup_observability(console_exporter=True)

        # Production with OTLP collector
        setup_observability(otlp_endpoint="http://otel-collector:4317")

        # Using environment variables
        # Set OTEL_EXPORTER_OTLP_ENDPOINT, then:
        setup_observability()
    """
    global _tracer_provider, _initialized

    if _initialized:
        logger.debug("Observability already initialized")
        return True

    # Build config from parameters or defaults
    if config is None:
        config = ObservabilityConfig(
            service_name=service_name or os.getenv("OTEL_SERVICE_NAME") or "corpus-callosum",
            otlp_endpoint=otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            console_exporter=console_exporter
            if console_exporter is not None
            else os.getenv("OTEL_CONSOLE_EXPORTER", "").lower() == "true",
        )

    if not config.enabled:
        logger.info("Observability disabled by config")
        return False

    try:
        from opentelemetry import trace

        # Set up tracer provider
        _tracer_provider = _setup_tracer_provider(config)
        trace.set_tracer_provider(_tracer_provider)

        # Auto-instrument libraries
        _instrument_fastapi()
        _instrument_httpx()

        # Set up OpenLLMetry if enabled
        if config.openllmetry_enabled:
            _setup_openllmetry()

        _initialized = True
        logger.info(
            "Observability initialized for service: %s",
            config.service_name,
        )
        return True

    except ImportError as e:
        logger.warning(
            "OpenTelemetry not available: %s. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk",
            e,
        )
        return False
    except Exception as e:
        logger.error("Failed to initialize observability: %s", e)
        return False


@lru_cache(maxsize=1)
def get_tracer(name: str = "corpus_callosum") -> Tracer:
    """Get an OpenTelemetry tracer for creating custom spans.

    Args:
        name: Tracer name (usually module name)

    Returns:
        Tracer instance (or no-op tracer if not initialized)

    Example:
        tracer = get_tracer()
        with tracer.start_as_current_span("retrieve_documents") as span:
            span.set_attribute("collection", collection_name)
            span.set_attribute("query_length", len(query))
            results = retriever.retrieve(query)
            span.set_attribute("num_results", len(results))
    """
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        # Return a no-op tracer if OpenTelemetry isn't installed
        from contextlib import contextmanager

        class NoOpSpan:
            def set_attribute(self, key: str, value: Any) -> None:
                pass

            def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
                pass

            def record_exception(self, exception: Exception) -> None:
                pass

        class NoOpTracer:
            @contextmanager
            def start_as_current_span(self, _name: str, **_kwargs: Any) -> Any:
                yield NoOpSpan()

        return NoOpTracer()  # type: ignore[return-value]


def trace_rag_query(
    query: str,
    collection: str,
    num_chunks: int,
    latency_ms: float | None = None,
) -> None:
    """Record a RAG query event with attributes.

    This is a convenience function for recording RAG-specific telemetry.

    Args:
        query: The user's query
        collection: Collection being queried
        num_chunks: Number of chunks retrieved
        latency_ms: Query latency in milliseconds
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        span.set_attribute("rag.query_length", len(query))
        span.set_attribute("rag.collection", collection)
        span.set_attribute("rag.num_chunks_retrieved", num_chunks)
        if latency_ms is not None:
            span.set_attribute("rag.latency_ms", latency_ms)
    except ImportError:
        pass  # No-op if not installed


def trace_llm_call(
    model: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: float | None = None,
) -> None:
    """Record an LLM call event with attributes.

    Args:
        model: Model name/identifier
        prompt_tokens: Number of prompt tokens (if known)
        completion_tokens: Number of completion tokens (if known)
        latency_ms: Call latency in milliseconds
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        span.set_attribute("llm.model", model)
        if prompt_tokens is not None:
            span.set_attribute("llm.prompt_tokens", prompt_tokens)
        if completion_tokens is not None:
            span.set_attribute("llm.completion_tokens", completion_tokens)
        if latency_ms is not None:
            span.set_attribute("llm.latency_ms", latency_ms)
    except ImportError:
        pass  # No-op if not installed


def shutdown_observability() -> None:
    """Gracefully shutdown observability, flushing any pending telemetry."""
    global _tracer_provider, _initialized

    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
            logger.info("Observability shutdown complete")
        except Exception as e:
            logger.error("Error during observability shutdown: %s", e)
    _tracer_provider = None
    _initialized = False
    get_tracer.cache_clear()
