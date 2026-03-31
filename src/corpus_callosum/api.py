"""FastAPI application for CorpusCallosum."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import TYPE_CHECKING

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import RagAgent
from .config import get_config
from .ingest import Ingester
from .retriever import HybridRetriever
from .security import (
    APIKeyAuth,
    AuthConfig,
    RateLimitConfig,
    RateLimiter,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

logger = logging.getLogger(__name__)


def _init_observability() -> None:
    """Initialize observability if configured and available."""
    config = get_config()
    if not config.observability.enabled:
        return

    try:
        from .observability import ObservabilityConfig as OtelConfig
        from .observability import setup_observability

        otel_config = OtelConfig(
            enabled=True,
            service_name=config.observability.service_name,
            otlp_endpoint=config.observability.otlp_endpoint,
            console_exporter=config.observability.console_exporter,
            openllmetry_enabled=config.observability.openllmetry_enabled,
        )
        setup_observability(otel_config)
    except ImportError:
        logger.warning(
            "Observability enabled but opentelemetry not installed. "
            "Install with: pip install corpus-callosum[observability]"
        )


def _shutdown_observability() -> None:
    """Shutdown observability gracefully."""
    try:
        from .observability import shutdown_observability

        shutdown_observability()
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events for startup/shutdown."""
    # Startup
    _init_observability()
    logger.info("CorpusCallosum API started")
    yield
    # Shutdown
    _shutdown_observability()
    logger.info("CorpusCallosum API stopped")


# Initialize app with OpenAPI metadata
app = FastAPI(
    title="CorpusCallosum API",
    version="0.1.0",
    description="Local-first RAG service with hybrid retrieval (semantic + BM25)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Lazy-initialized security components
_rate_limiter: RateLimiter | None = None
_api_key_auth: APIKeyAuth | None = None


def _get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        config = get_config()
        _rate_limiter = RateLimiter(
            RateLimitConfig(
                enabled=config.security.rate_limit_enabled,
                requests_per_minute=config.security.requests_per_minute,
                requests_per_hour=config.security.requests_per_hour,
                burst_limit=config.security.burst_limit,
            )
        )
    return _rate_limiter


def _get_api_key_auth() -> APIKeyAuth:
    global _api_key_auth
    if _api_key_auth is None:
        config = get_config()
        _api_key_auth = APIKeyAuth(
            AuthConfig(
                enabled=config.security.auth_enabled,
                api_keys=list(config.security.api_keys),
                keys_are_hashed=config.security.api_keys_hashed,
            )
        )
    return _api_key_auth


def verify_request(
    request: Request,
    api_key: str | None = Depends(lambda: None),
) -> None:
    """Combined dependency for rate limiting and authentication."""
    # Check rate limit
    _get_rate_limiter().check_rate_limit(request)
    # Check API key if auth is enabled
    _get_api_key_auth().verify(api_key)


# Custom dependency that extracts API key from header
async def get_api_key(request: Request) -> str | None:
    """Extract API key from request header."""
    return request.headers.get("X-API-Key")


async def security_dependency(
    request: Request,
    api_key: str | None = Depends(get_api_key),
) -> None:
    """Combined security checks: rate limiting and authentication."""
    _get_rate_limiter().check_rate_limit(request)
    _get_api_key_auth().verify(api_key)


@lru_cache(maxsize=1)
def _get_ingester() -> Ingester:
    return Ingester()


@lru_cache(maxsize=1)
def _get_agent() -> RagAgent:
    return RagAgent()


@lru_cache(maxsize=1)
def _get_retriever() -> HybridRetriever:
    return HybridRetriever()


# Request/Response models with OpenAPI examples
class IngestRequest(BaseModel):
    """Request to ingest documents into a collection."""

    file_path: str = Field(
        ...,
        description="Directory or file path to ingest",
        examples=["./vault/biology", "/data/documents/chapter1.pdf"],
    )
    collection: str = Field(
        ...,
        description="Target collection name",
        examples=["biology101", "research_papers"],
    )


class IngestResponse(BaseModel):
    """Response from document ingestion."""

    collection: str = Field(..., description="Collection name")
    files_indexed: int = Field(..., description="Number of files processed")
    chunks_indexed: int = Field(..., description="Number of chunks created")


class QueryRequest(BaseModel):
    """Request to query a collection."""

    query: str = Field(
        ...,
        description="Question to ask",
        examples=["What is photosynthesis?", "Explain the main concepts"],
    )
    collection: str = Field(
        ...,
        description="Collection to search",
        examples=["biology101"],
    )


class CritiqueRequest(BaseModel):
    """Request for writing critique."""

    essay_text: str = Field(
        ...,
        description="Essay text to critique",
        examples=["Climate change is a significant challenge facing humanity..."],
    )


class FlashcardsRequest(BaseModel):
    """Request to generate flashcards from a collection."""

    collection: str = Field(
        ...,
        description="Collection name to generate flashcards from",
        examples=["biology101"],
    )


class CollectionsResponse(BaseModel):
    """Response listing available collections."""

    collections: list[str] = Field(..., description="List of collection names")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")


class RateLimitInfo(BaseModel):
    """Rate limit information."""

    burst: int = Field(..., description="Remaining requests in current second")
    minute: int = Field(..., description="Remaining requests in current minute")
    hour: int = Field(..., description="Remaining requests in current hour")


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str = Field(..., description="Error message")


# Endpoints
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
    description="Returns the health status of the service.",
)
def health() -> dict[str, str]:
    """Check if the service is running."""
    return {"status": "ok"}


@app.get(
    "/rate-limit",
    response_model=RateLimitInfo,
    tags=["System"],
    summary="Check rate limit status",
    description="Returns remaining requests for the current client.",
    dependencies=[Depends(security_dependency)],
)
def rate_limit_status(request: Request) -> dict[str, int]:
    """Get rate limit information for the current client."""
    return _get_rate_limiter().get_remaining(request)


@app.post(
    "/ingest",
    response_model=IngestResponse,
    tags=["Documents"],
    summary="Ingest documents",
    description="Ingest documents from a file or directory into a collection.",
    responses={
        404: {"model": ErrorResponse, "description": "File or directory not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(security_dependency)],
)
def ingest(request: IngestRequest) -> JSONResponse:
    """Ingest documents into a collection for later querying."""
    ingester = _get_ingester()
    try:
        result = ingester.ingest_path(
            path=request.file_path,
            collection_name=request.collection,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during ingestion",
        ) from exc

    return JSONResponse(
        {
            "collection": result.collection,
            "files_indexed": result.files_indexed,
            "chunks_indexed": result.chunks_indexed,
        }
    )


def _sse_stream(tokens: Iterator[str]) -> Iterator[str]:
    """Convert token iterator to Server-Sent Events format."""
    for token in tokens:
        text = str(token)
        lines = text.splitlines() or [""]
        for line in lines:
            yield f"data: {line}\n"
        yield "\n"
    yield "data: [DONE]\n\n"


@app.post(
    "/query",
    tags=["RAG"],
    summary="Query documents",
    description="Ask a question and get an AI-generated answer based on your documents. "
    "Returns a Server-Sent Events stream.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(security_dependency)],
)
def query(request: QueryRequest) -> StreamingResponse:
    """Query the RAG system with a question."""
    agent = _get_agent()
    try:
        tokens, _chunks = agent.query(
            query=request.query,
            collection_name=request.collection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during query",
        ) from exc

    return StreamingResponse(_sse_stream(tokens), media_type="text/event-stream")


@app.post(
    "/critique",
    tags=["RAG"],
    summary="Critique writing",
    description="Get AI-powered feedback on your writing. Returns a Server-Sent Events stream.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(security_dependency)],
)
def critique(request: CritiqueRequest) -> StreamingResponse:
    """Get writing critique and suggestions."""
    agent = _get_agent()
    try:
        tokens = agent.critique_writing(request.essay_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during critique",
        ) from exc

    return StreamingResponse(_sse_stream(tokens), media_type="text/event-stream")


@app.post(
    "/flashcards",
    tags=["RAG"],
    summary="Generate flashcards",
    description="Generate study flashcards from a collection. Returns a Server-Sent Events stream "
    "with cards in 'question::answer' format.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or empty collection"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(security_dependency)],
)
def flashcards(request: FlashcardsRequest) -> StreamingResponse:
    """Generate flashcards from collection content."""
    agent = _get_agent()
    try:
        tokens = agent.generate_flashcards(request.collection)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during flashcard generation",
        ) from exc

    return StreamingResponse(_sse_stream(tokens), media_type="text/event-stream")


@app.get(
    "/collections",
    response_model=CollectionsResponse,
    tags=["Documents"],
    summary="List collections",
    description="Get a list of all available document collections.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(security_dependency)],
)
def collections() -> JSONResponse:
    """List all available collections."""
    retriever = _get_retriever()
    try:
        names = retriever.list_collections()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"collections": names})


def main() -> None:
    """Start the API server."""
    config = get_config()
    uvicorn.run(
        "corpus_callosum.api:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
