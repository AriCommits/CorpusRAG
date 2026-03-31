"""OpenTelemetry metrics for RAG observability.

Provides custom metrics for:
- Query duration (histogram)
- Retrieval chunk counts (histogram)
- Token usage (counter)
- Error rates (counter)
- Collection sizes (gauge)
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class _NoOpHistogram:
    def record(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpCounter:
    def add(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpGauge:
    def set(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


_meter = None
_initialized = False

_query_duration: _NoOpHistogram | Any = _NoOpHistogram()
_retrieval_chunks: _NoOpHistogram | Any = _NoOpHistogram()
_llm_tokens: _NoOpCounter | Any = _NoOpCounter()
_errors_total: _NoOpCounter | Any = _NoOpCounter()
_collection_size: _NoOpGauge | Any = _NoOpGauge()


def init_metrics() -> bool:
    """Initialize OTel metrics. Returns True if successful."""
    global _meter, _initialized
    global _query_duration, _retrieval_chunks, _llm_tokens, _errors_total, _collection_size

    if _initialized:
        return True

    try:
        from opentelemetry import metrics

        _meter = metrics.get_meter("corpus_callosum")

        _query_duration = _meter.create_histogram(
            "rag.query.duration",
            unit="ms",
            description="Duration of RAG queries",
        )
        _retrieval_chunks = _meter.create_histogram(
            "rag.retrieval.num_chunks",
            unit="chunks",
            description="Number of chunks retrieved",
        )
        _llm_tokens = _meter.create_counter(
            "rag.llm.tokens.total",
            unit="tokens",
            description="Total tokens used",
        )
        _errors_total = _meter.create_counter(
            "rag.errors.total",
            unit="errors",
            description="Total errors by type",
        )
        _collection_size = _meter.create_gauge(
            "rag.collection.size",
            unit="documents",
            description="Number of documents in a collection",
        )

        _initialized = True
        logger.info("OTel metrics initialized")
        return True

    except ImportError:
        logger.debug("OpenTelemetry metrics not available")
        return False
    except Exception as exc:
        logger.error("Failed to initialize metrics: %s", exc)
        return False


@contextmanager
def measure_query_duration(collection: str, model: str) -> Iterator[None]:
    """Context manager to measure RAG query duration."""
    start = time.monotonic()
    try:
        yield
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        _query_duration.record(
            duration_ms,
            attributes={"collection": collection, "model": model},
        )


def record_retrieval(num_chunks: int, collection: str) -> None:
    _retrieval_chunks.record(
        float(num_chunks),
        attributes={"collection": collection},
    )


def record_tokens(prompt: int, completion: int, model: str) -> None:
    _llm_tokens.add(
        float(prompt + completion),
        attributes={"model": model, "type": "total"},
    )


def record_error(error_type: str, collection: str | None = None) -> None:
    attrs: dict[str, str] = {"error_type": error_type}
    if collection:
        attrs["collection"] = collection
    _errors_total.add(1.0, attributes=attrs)


def record_collection_size(size: int, collection: str) -> None:
    _collection_size.set(
        float(size),
        attributes={"collection": collection},
    )
