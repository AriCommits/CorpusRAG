from unittest.mock import MagicMock, patch

import pytest

from tools.rag.config import RAGConfig
from tools.rag.ingest import IngestResult
from tools.rag.sync import RAGSyncer


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.collection_exists.return_value = True
    return db


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock(spec=RAGConfig)
    config.collection_prefix = "test"

    # Mock parent_store path as a Path object
    parent_store_path = tmp_path / "parent_store"
    config.parent_store = MagicMock()
    config.parent_store.path = parent_store_path

    # Mock chunking settings to avoid AttributeError
    config.chunking = MagicMock()
    config.chunking.child_chunk_size = 100
    config.chunking.child_chunk_overlap = 20

    return config


def test_rag_syncer_init(mock_config, mock_db):
    syncer = RAGSyncer(mock_config, mock_db)
    assert syncer.config == mock_config
    assert syncer.db == mock_db


@patch("tools.rag.sync.RAGIngester")
def test_sync_dry_run(mock_ingester_class, mock_config, mock_db, tmp_path):
    # Setup mock ingester
    mock_ingester = mock_ingester_class.return_value
    mock_ingester._iter_source_files.return_value = [tmp_path / "test.txt"]
    mock_ingester._read_file.return_value = "content"

    # Set parent_store on the mock ingester explicitly to avoid AttributeError
    mock_ingester.parent_store = MagicMock()

    # Setup mock db
    mock_db.get_collection.return_value.get.return_value = {
        "metadatas": [{"source_file": "test.txt", "file_hash": "wrong_hash"}]
    }

    syncer = RAGSyncer(mock_config, mock_db)
    syncer.ingester = mock_ingester

    # Create test file
    (tmp_path / "test.txt").write_text("content")

    result = syncer.sync(tmp_path, "col", dry_run=True)

    assert result.collection == "col"
    assert result.modified_files == ["test.txt"]
    assert result.chunks_added == 0
    assert result.chunks_removed == 0


@patch("tools.rag.sync.RAGIngester")
def test_sync_apply(mock_ingester_class, mock_config, mock_db, tmp_path):
    # Setup mock ingester
    mock_ingester = mock_ingester_class.return_value
    mock_ingester._iter_source_files.return_value = [tmp_path / "new.txt"]
    mock_ingester._read_file.return_value = "content"
    mock_ingester.ingest_path.return_value = IngestResult("col", 1, 5)

    # Set parent_store explicitly
    mock_ingester.parent_store = MagicMock()

    # Setup mock db to return a deleted file
    mock_db.get_collection.return_value.get.return_value = {
        "metadatas": [{"source_file": "deleted.txt", "file_hash": "hash"}]
    }

    syncer = RAGSyncer(mock_config, mock_db)
    syncer.ingester = mock_ingester

    # Create test file
    (tmp_path / "new.txt").write_text("content")

    result = syncer.sync(tmp_path, "col", dry_run=False)

    assert result.new_files == ["new.txt"]
    assert result.deleted_files == ["deleted.txt"]
    assert result.chunks_added == 5
