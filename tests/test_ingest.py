"""Tests for document ingestion."""

from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corpus_callosum.ingest import Ingester, IngestResult


@pytest.fixture
def mock_chroma_client():
    """Create a mock ChromaDB client."""
    client = MagicMock()
    client.get_or_create_collection.return_value = MagicMock()
    return client


def test_ingest_result_dataclass():
    """Test IngestResult dataclass creation."""
    result = IngestResult(collection="test_collection", files_indexed=5, chunks_indexed=10)

    assert result.collection == "test_collection"
    assert result.files_indexed == 5
    assert result.chunks_indexed == 10


def test_ingester_initialization(mock_chroma_client):
    """Test that Ingester initializes correctly."""
    ingester = Ingester(chroma_client=mock_chroma_client)
    assert ingester.config is not None
    assert ingester.client is not None
    # embedding_backend is lazily loaded, so accessing the property will load it
    # We just test that the attribute exists (it's a property that loads on access)
    assert hasattr(ingester, "_embedding_backend")


def test_chunk_text_empty(mock_chroma_client):
    """Test chunking empty text."""
    ingester = Ingester(chroma_client=mock_chroma_client)
    chunks = ingester._chunk_text("")
    assert chunks == []


def test_chunk_text_short(mock_chroma_client):
    """Test chunking text shorter than chunk size."""
    ingester = Ingester(chroma_client=mock_chroma_client)
    # Create a custom config for testing (can't modify frozen dataclass)

    # Create a copy of the config with different chunking settings
    custom_config = replace(
        ingester.config, chunking=replace(ingester.config.chunking, size=100, overlap=20)
    )

    # Create ingester with custom config
    ingester_custom = Ingester(config=custom_config, chroma_client=mock_chroma_client)

    text = "This is a short text."
    chunks = ingester_custom._chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long(mock_chroma_client):
    """Test chunking text longer than chunk size."""
    ingester = Ingester(chroma_client=mock_chroma_client)
    # Create a custom config for testing (can't modify frozen dataclass)

    # Create a copy of the config with different chunking settings
    custom_config = replace(
        ingester.config, chunking=replace(ingester.config.chunking, size=10, overlap=2)
    )

    # Create ingester with custom config
    ingester_custom = Ingester(config=custom_config, chroma_client=mock_chroma_client)

    text = "This is a longer text that should be split into multiple chunks."
    chunks = ingester_custom._chunk_text(text)

    # Should have multiple chunks
    assert len(chunks) > 1

    # All chunks should be non-empty
    assert all(chunk.strip() for chunk in chunks)

    # When joined with spaces, should contain all original words (approximately)
    # Note: exact reconstruction isn't guaranteed due to overlap handling
    joined = " ".join(chunks)
    original_words = set(text.split())
    joined_words = set(joined.split())
    # Most original words should be present
    assert len(original_words & joined_words) >= len(original_words) * 0.8


def test_build_chunk_id(mock_chroma_client):
    """Test chunk ID generation."""
    ingester = Ingester(chroma_client=mock_chroma_client)

    chunk_id = ingester._build_chunk_id(
        collection_name="test", source_file="doc.pdf", chunk_index=0, text="Hello world"
    )

    # Should follow format: collection:source_file:chunk_index:hash
    parts = chunk_id.split(":")
    assert len(parts) == 4
    assert parts[0] == "test"
    assert parts[1] == "doc.pdf"
    assert parts[2] == "0"
    assert len(parts[3]) == 12  # SHA1 truncated to 12 chars


def test_iter_source_files_file(mock_chroma_client):
    """Test _iter_source_files with a single file."""
    ingester = Ingester(chroma_client=mock_chroma_client)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create a markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test")

        # Create a txt file (also supported)
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Text file supported")

        # Create a non-supported file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b,c")

        files = list(ingester._iter_source_files(md_file))
        assert len(files) == 1
        # Compare resolved paths to handle any symbolic links
        assert files[0].resolve() == md_file.resolve()

        files = list(ingester._iter_source_files(txt_file))
        assert len(files) == 1  # .txt is in SUPPORTED_EXTENSIONS

        files = list(ingester._iter_source_files(csv_file))
        assert len(files) == 0  # .csv is not in SUPPORTED_EXTENSIONS


def test_iter_source_files_directory(mock_chroma_client):
    """Test _iter_source_files with a directory."""
    ingester = Ingester(chroma_client=mock_chroma_client)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create markdown files
        md1 = tmp_path / "doc1.md"
        md1.write_text("# Doc 1")
        md2 = tmp_path / "subdir" / "doc2.md"
        md2.parent.mkdir()
        md2.write_text("# Doc 2")
        # Create a PDF file (should be supported)
        pdf_file = tmp_path / "other.pdf"
        pdf_file.write_text("% PDF")

        files = list(ingester._iter_source_files(tmp_path))
        # Should find both markdown files and the PDF file, sorted
        assert len(files) == 3
        # Check that all expected files are present (order may vary)
        file_names = {f.name for f in files}
        assert "doc1.md" in file_names
        assert "doc2.md" in file_names
        assert "other.pdf" in file_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
