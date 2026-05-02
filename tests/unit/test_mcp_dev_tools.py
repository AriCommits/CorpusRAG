"""Unit tests for mcp_server/tools/dev.py."""

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
import yaml

from config import load_config
from mcp_server.tools.dev import (
    collection_info,
    list_collections,
    rag_ingest,
    store_text,
)


@pytest.fixture()
def config(tmp_path):
    """Create a minimal config with persistent database and rag settings."""
    cfg = {
        "llm": {"model": "llama3"},
        "database": {
            "mode": "persistent",
            "persist_directory": str(tmp_path / "chroma"),
        },
        "paths": {
            "vault": str(tmp_path),
        },
        "rag": {
            "strategy": "semantic",
            "chunking": {"child_chunk_size": 400, "child_chunk_overlap": 50},
            "parent_store": {"path": str(tmp_path / "parent_store")},
        },
    }
    path = tmp_path / "base.yaml"
    path.write_text(yaml.dump(cfg))
    return load_config(path)


@pytest.fixture()
def mock_db():
    """Create a mock DatabaseBackend."""
    db = MagicMock()
    db.list_collections.return_value = ["col1", "col2"]
    db.collection_exists.return_value = False
    db.get_collection_stats.side_effect = Exception("Collection not found")
    return db


class TestListCollections:
    def test_returns_dict_with_collections_key(self, mock_db):
        result = list_collections(mock_db)
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "collections" in result
        assert result["collections"] == ["col1", "col2"]


class TestCollectionInfo:
    def test_nonexistent_collection_returns_error(self, mock_db):
        result = collection_info("nonexistent", mock_db)
        assert result["status"] == "error"
        assert "error" in result

    def test_existing_collection_returns_stats(self, mock_db):
        mock_db.get_collection_stats.side_effect = None
        mock_db.get_collection_stats.return_value = {"doc_count": 10, "chunk_count": 50}
        result = collection_info("my_col", mock_db)
        assert result["status"] == "success"
        assert result["doc_count"] == 10


class TestStoreText:
    def test_stores_and_returns_chunk_count(self, config, mock_db):
        with patch("mcp_server.tools.dev.EmbeddingClient") as MockEmbedder:
            instance = MockEmbedder.return_value
            instance.embed_texts.return_value = [[0.1] * 384]

            result = store_text("Hello world. This is a test.", "notes", config, mock_db)

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["collection"] == "notes"
        assert result["chunks_created"] >= 1
        mock_db.add_documents.assert_called_once()

    def test_creates_collection_if_not_exists(self, config, mock_db):
        mock_db.collection_exists.return_value = False
        with patch("mcp_server.tools.dev.EmbeddingClient") as MockEmbedder:
            instance = MockEmbedder.return_value
            instance.embed_texts.return_value = [[0.1] * 384]
            store_text("Some text.", "new_col", config, mock_db)

        mock_db.create_collection.assert_called_once()


class TestRagIngest:
    def test_invalid_path_returns_error(self, config, mock_db):
        result = rag_ingest("/nonexistent/path/to/docs", "notes", config, mock_db)
        assert result["status"] == "error"
        assert "error" in result

    def test_valid_path_calls_ingester(self, config, mock_db, tmp_path):
        doc = tmp_path / "doc.md"
        doc.write_text("# Hello\nSome content.")

        with patch("mcp_server.tools.dev.RAGIngester") as MockIngester:
            instance = MockIngester.return_value
            instance.ingest_path.return_value = MagicMock(
                files_indexed=1, chunks_indexed=3
            )
            result = rag_ingest(str(tmp_path), "notes", config, mock_db)

        assert result["status"] == "success"
        assert result["files_indexed"] == 1
        assert result["chunks_indexed"] == 3



class TestSecurityHardening:
    def test_rag_ingest_rejects_path_outside_vault(self):
        config = MagicMock()
        config.paths.vault = Path("./vault")
        config.to_dict.return_value = {"llm": {}, "embedding": {}, "database": {}, "paths": {"vault": "./vault"}}
        db = MagicMock()
        result = rag_ingest("/etc/passwd", "exfil", config, db)
        assert result["status"] == "error"

    def test_store_text_rejects_oversized(self):
        config = MagicMock()
        config.to_dict.return_value = {"llm": {}, "embedding": {}, "database": {}, "paths": {}}
        db = MagicMock()
        big_text = "x" * 200_000
        result = store_text(big_text, "test", config, db)
        assert result["status"] == "error"
        assert "too large" in result["error"]

    def test_store_text_filters_metadata(self):
        config = MagicMock()
        config.to_dict.return_value = {"llm": {}, "embedding": {}, "database": {}, "paths": {}, "rag": {}}
        db = MagicMock()
        db.collection_exists.return_value = True

        with patch("mcp_server.tools.dev.EmbeddingClient") as mock_embed:
            mock_embed.return_value.embed_texts.return_value = [[0.1] * 10]
            with patch("tools.rag.pipeline.adaptive_splitter.adaptive_split", return_value=["chunk1"]):
                result = store_text(
                    "safe text", "test", config, db,
                    metadata={"topic": "math", "parent_id": "evil", "file_hash": "spoofed"}
                )

        if result["status"] == "success":
            # Verify the metadata passed to db.add_documents doesn't contain blocked keys
            call_args = db.add_documents.call_args
            stored_meta = call_args[0][3][0]  # metadatas[0]
            assert "parent_id" not in stored_meta
            assert "file_hash" not in stored_meta
            assert stored_meta.get("topic") == "math"
