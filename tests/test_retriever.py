"""Tests for the hybrid retriever."""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from corpus_callosum.retriever import (
    HybridRetriever,
    RetrievedChunk,
    _normalize_token,
    _tokenize,
)


class TestTokenization:
    """Tests for tokenization utilities."""

    def test_normalize_token_lowercase(self):
        """Test that normalization lowercases tokens."""
        assert _normalize_token("Hello") == "hello"
        assert _normalize_token("WORLD") == "world"

    def test_normalize_token_removes_punctuation(self):
        """Test that normalization removes punctuation."""
        assert _normalize_token("hello!") == "hello"
        assert _normalize_token("world?") == "world"
        assert _normalize_token("test.") == "test"

    def test_normalize_token_keeps_alphanumeric(self):
        """Test that normalization keeps alphanumeric characters."""
        assert _normalize_token("test123") == "test123"
        assert _normalize_token("abc456xyz") == "abc456xyz"

    def test_tokenize_basic(self):
        """Test basic tokenization."""
        result = _tokenize("Hello World")
        assert result == ["hello", "world"]

    def test_tokenize_with_punctuation(self):
        """Test tokenization with punctuation."""
        result = _tokenize("Hello, World! How are you?")
        assert result == ["hello", "world", "how", "are", "you"]

    def test_tokenize_empty_string(self):
        """Test tokenization of empty string."""
        assert _tokenize("") == []

    def test_tokenize_filters_empty_tokens(self):
        """Test that tokenization filters out empty tokens."""
        result = _tokenize("   hello    world   ")
        assert result == ["hello", "world"]


class TestRetrievedChunk:
    """Tests for RetrievedChunk dataclass."""

    def test_chunk_creation(self):
        """Test creating a chunk with all fields."""
        chunk = RetrievedChunk(
            id="test:file:0:abc123",
            text="This is test content",
            metadata={"source_file": "test.md"},
            semantic_rank=1,
            bm25_rank=2,
            score=0.5,
        )
        assert chunk.id == "test:file:0:abc123"
        assert chunk.text == "This is test content"
        assert chunk.metadata == {"source_file": "test.md"}
        assert chunk.semantic_rank == 1
        assert chunk.bm25_rank == 2
        assert chunk.score == 0.5

    def test_chunk_default_values(self):
        """Test chunk with default values."""
        chunk = RetrievedChunk(
            id="test:file:0:abc123",
            text="Content",
            metadata={},
        )
        assert chunk.semantic_rank is None
        assert chunk.bm25_rank is None
        assert chunk.score == 0.0

    def test_chunk_is_frozen(self):
        """Test that chunk is immutable."""
        chunk = RetrievedChunk(id="test", text="content", metadata={})
        with pytest.raises(AttributeError):
            chunk.id = "new_id"  # type: ignore


class TestHybridRetriever:
    """Tests for HybridRetriever class."""

    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client."""
        client = MagicMock()
        collection = MagicMock()
        collection.count.return_value = 3
        collection.get.return_value = {
            "ids": ["id1", "id2", "id3"],
            "documents": ["doc one content", "doc two content", "doc three content"],
            "metadatas": [{"source_file": "a.md"}, {"source_file": "b.md"}, {"source_file": "c.md"}],
        }
        collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc one content", "doc two content"]],
            "metadatas": [[{"source_file": "a.md"}, {"source_file": "b.md"}]],
            "distances": [[0.1, 0.2]],
        }
        client.get_collection.return_value = collection
        client.list_collections.return_value = [
            MagicMock(name="collection1"),
            MagicMock(name="collection2"),
        ]
        return client

    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        model = MagicMock()
        # Return a numpy array that has tolist() method
        model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        return model

    @pytest.fixture
    def retriever(self, mock_chroma_client, mock_embedding_model):
        """Create a retriever with mocked dependencies."""
        return HybridRetriever(
            chroma_client=mock_chroma_client,
            embedding_model=mock_embedding_model,
        )

    def test_semantic_search_returns_chunks(self, retriever):
        """Test that semantic search returns ranked chunks."""
        result = retriever.semantic_search(query="test query", collection_name="test")

        assert len(result) == 2
        assert result[0].id == "id1"
        assert result[0].semantic_rank == 1
        assert result[1].id == "id2"
        assert result[1].semantic_rank == 2

    def test_semantic_search_empty_collection(self, mock_chroma_client, mock_embedding_model):
        """Test semantic search on empty collection."""
        collection = MagicMock()
        collection.count.return_value = 0
        mock_chroma_client.get_collection.return_value = collection

        retriever = HybridRetriever(
            chroma_client=mock_chroma_client,
            embedding_model=mock_embedding_model,
        )
        result = retriever.semantic_search(query="test", collection_name="empty")
        assert result == []

    def test_semantic_search_nonexistent_collection(self, mock_chroma_client, mock_embedding_model):
        """Test semantic search on non-existent collection."""
        mock_chroma_client.get_collection.side_effect = Exception("Collection not found")

        retriever = HybridRetriever(
            chroma_client=mock_chroma_client,
            embedding_model=mock_embedding_model,
        )
        result = retriever.semantic_search(query="test", collection_name="nonexistent")
        assert result == []

    def test_bm25_search_returns_chunks(self, retriever):
        """Test that BM25 search returns ranked chunks."""
        result = retriever.bm25_search(query="doc one", collection_name="test")

        assert len(result) > 0
        # First result should have bm25_rank of 1
        assert result[0].bm25_rank == 1

    def test_bm25_search_empty_query(self, retriever):
        """Test BM25 search with empty query tokens."""
        # Query with only punctuation will result in empty tokens
        result = retriever.bm25_search(query="!!!", collection_name="test")
        assert result == []

    def test_retrieve_combines_results(self, retriever):
        """Test that retrieve combines semantic and BM25 results."""
        result = retriever.retrieve(query="doc content", collection_name="test")

        assert len(result) > 0
        # Results should have RRF scores
        assert all(chunk.score > 0 for chunk in result)

    def test_retrieve_merges_duplicate_chunks(self, retriever):
        """Test that duplicate chunks are merged correctly."""
        result = retriever.retrieve(query="doc one", collection_name="test")

        # Check that chunks have both semantic and bm25 ranks where applicable
        ids = [chunk.id for chunk in result]
        # No duplicate IDs
        assert len(ids) == len(set(ids))

    def test_list_collections(self, retriever, mock_chroma_client):
        """Test listing collections."""
        # Mock the list_collections to return proper collection objects
        mock_col1 = MagicMock()
        mock_col1.name = "alpha"
        mock_col2 = MagicMock()
        mock_col2.name = "beta"
        mock_chroma_client.list_collections.return_value = [mock_col1, mock_col2]

        result = retriever.list_collections()
        assert result == ["alpha", "beta"]

    def test_collection_documents(self, retriever):
        """Test getting all documents from a collection."""
        result = retriever.collection_documents("test")

        assert len(result) == 3
        assert result[0].id == "id1"
        assert result[0].text == "doc one content"


class TestHybridRetrieverRRF:
    """Tests for RRF (Reciprocal Rank Fusion) scoring."""

    def test_rrf_score_calculation(self):
        """Test that RRF scores are calculated correctly."""
        # Create a retriever with mocked data where we control rankings
        mock_client = MagicMock()
        collection = MagicMock()
        collection.count.return_value = 2

        # Set up semantic results
        collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["first doc", "second doc"]],
            "metadatas": [[{}, {}]],
            "distances": [[0.1, 0.2]],
        }

        # Set up BM25 results (same docs, reversed order)
        collection.get.return_value = {
            "ids": ["id1", "id2"],
            "documents": ["first doc", "second doc"],
            "metadatas": [{}, {}],
        }

        mock_client.get_collection.return_value = collection

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])

        retriever = HybridRetriever(
            chroma_client=mock_client,
            embedding_model=mock_model,
        )

        result = retriever.retrieve(query="first", collection_name="test")

        # Both docs should have scores > 0
        assert all(chunk.score > 0 for chunk in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
