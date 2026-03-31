"""Integration tests for API endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import corpus_callosum.api as api_module
from corpus_callosum.api import app
from corpus_callosum.ingest import IngestResult
from corpus_callosum.retriever import RetrievedChunk
from corpus_callosum.security import RateLimitConfig, RateLimiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test to avoid cross-test interference."""
    # Create a fresh rate limiter with high limits for testing
    api_module._rate_limiter = RateLimiter(
        RateLimitConfig(
            enabled=True,
            requests_per_minute=1000,
            requests_per_hour=10000,
            burst_limit=100,
        )
    )
    yield
    # Clean up after test
    api_module._rate_limiter = None


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Test that health endpoint returns OK status."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestIngestEndpoint:
    """Tests for /ingest endpoint."""

    def test_ingest_success(self, client):
        """Test successful document ingestion."""
        mock_result = IngestResult(
            collection="test_collection",
            files_indexed=3,
            chunks_indexed=15,
        )

        with patch("corpus_callosum.api._get_ingester") as mock_get:
            mock_ingester = MagicMock()
            mock_ingester.ingest_path.return_value = mock_result
            mock_get.return_value = mock_ingester

            response = client.post(
                "/ingest",
                json={"file_path": "./vault/docs", "collection": "test_collection"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["collection"] == "test_collection"
            assert data["files_indexed"] == 3
            assert data["chunks_indexed"] == 15

    def test_ingest_file_not_found(self, client):
        """Test ingest with non-existent file path."""
        with patch("corpus_callosum.api._get_ingester") as mock_get:
            mock_ingester = MagicMock()
            mock_ingester.ingest_path.side_effect = FileNotFoundError("Path not found")
            mock_get.return_value = mock_ingester

            response = client.post(
                "/ingest",
                json={"file_path": "./nonexistent", "collection": "test"},
            )

            assert response.status_code == 404
            assert "Path not found" in response.json()["detail"]

    def test_ingest_validation_error(self, client):
        """Test ingest with invalid parameters."""
        with patch("corpus_callosum.api._get_ingester") as mock_get:
            mock_ingester = MagicMock()
            mock_ingester.ingest_path.side_effect = ValueError("Invalid collection name")
            mock_get.return_value = mock_ingester

            response = client.post(
                "/ingest",
                json={"file_path": "./vault", "collection": ""},
            )

            assert response.status_code == 400

    def test_ingest_missing_fields(self, client):
        """Test ingest with missing required fields."""
        response = client.post("/ingest", json={"file_path": "./vault"})

        assert response.status_code == 422  # Validation error


class TestQueryEndpoint:
    """Tests for /query endpoint."""

    def test_query_returns_sse_stream(self, client):
        """Test that query returns a server-sent event stream."""
        mock_chunks = [
            RetrievedChunk(
                id="test:doc:0:abc",
                text="Context text",
                metadata={"source_file": "doc.md"},
                score=0.5,
            )
        ]

        with patch("corpus_callosum.api._get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_agent.query.return_value = (iter(["Hello", " ", "World"]), mock_chunks)
            mock_get.return_value = mock_agent

            response = client.post(
                "/query",
                json={"query": "What is this?", "collection": "test"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Check SSE format
            content = response.text
            assert "data: Hello" in content
            assert "data: World" in content
            assert "data: [DONE]" in content

    def test_query_validation_error(self, client):
        """Test query with validation error."""
        with patch("corpus_callosum.api._get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_agent.query.side_effect = ValueError("Collection not found")
            mock_get.return_value = mock_agent

            response = client.post(
                "/query",
                json={"query": "test", "collection": "nonexistent"},
            )

            assert response.status_code == 400

    def test_query_missing_fields(self, client):
        """Test query with missing required fields."""
        response = client.post("/query", json={"query": "test"})

        assert response.status_code == 422


class TestCritiqueEndpoint:
    """Tests for /critique endpoint."""

    def test_critique_returns_sse_stream(self, client):
        """Test that critique returns a server-sent event stream."""
        with patch("corpus_callosum.api._get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_agent.critique_writing.return_value = iter(["Good", " ", "essay"])
            mock_get.return_value = mock_agent

            response = client.post(
                "/critique",
                json={"essay_text": "This is my essay about testing."},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            content = response.text
            assert "data: Good" in content
            assert "data: essay" in content
            assert "data: [DONE]" in content

    def test_critique_missing_fields(self, client):
        """Test critique with missing required fields."""
        response = client.post("/critique", json={})

        assert response.status_code == 422


class TestFlashcardsEndpoint:
    """Tests for /flashcards endpoint."""

    def test_flashcards_returns_sse_stream(self, client):
        """Test that flashcards returns a server-sent event stream."""
        with patch("corpus_callosum.api._get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_agent.generate_flashcards.return_value = iter(["Q1::A1\n", "Q2::A2"])
            mock_get.return_value = mock_agent

            response = client.post(
                "/flashcards",
                json={"collection": "biology"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_flashcards_validation_error(self, client):
        """Test flashcards with empty collection."""
        with patch("corpus_callosum.api._get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_agent.generate_flashcards.side_effect = ValueError("No chunks found")
            mock_get.return_value = mock_agent

            response = client.post(
                "/flashcards",
                json={"collection": "empty"},
            )

            assert response.status_code == 400


class TestCollectionsEndpoint:
    """Tests for /collections endpoint."""

    def test_collections_returns_list(self, client):
        """Test that collections endpoint returns a list."""
        with patch("corpus_callosum.api._get_retriever") as mock_get:
            mock_retriever = MagicMock()
            mock_retriever.list_collections.return_value = ["bio101", "chem201", "physics"]
            mock_get.return_value = mock_retriever

            response = client.get("/collections")

            assert response.status_code == 200
            data = response.json()
            assert "collections" in data
            assert data["collections"] == ["bio101", "chem201", "physics"]

    def test_collections_empty(self, client):
        """Test collections endpoint with no collections."""
        with patch("corpus_callosum.api._get_retriever") as mock_get:
            mock_retriever = MagicMock()
            mock_retriever.list_collections.return_value = []
            mock_get.return_value = mock_retriever

            response = client.get("/collections")

            assert response.status_code == 200
            assert response.json()["collections"] == []


class TestSSEFormat:
    """Tests for SSE stream formatting."""

    def test_sse_multiline_handling(self, client):
        """Test that multiline tokens are handled correctly in SSE."""
        with patch("corpus_callosum.api._get_agent") as mock_get:
            mock_agent = MagicMock()
            # Token with newline
            mock_agent.critique_writing.return_value = iter(["Line1\nLine2"])
            mock_get.return_value = mock_agent

            response = client.post(
                "/critique",
                json={"essay_text": "test"},
            )

            content = response.text
            # Each line should be a separate data field
            assert "data: Line1" in content
            assert "data: Line2" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
