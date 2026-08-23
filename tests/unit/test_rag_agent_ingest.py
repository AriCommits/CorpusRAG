"""Tests for RAGAgent.ingest_text and get_ingested_hashes."""

from unittest.mock import MagicMock, patch

from tools.rag.agent import RAGAgent
from tools.rag.config import RAGConfig
from tools.rag.ingest import IngestResult, RAGIngester


def test_agent_ingest_text_and_hashes_match_handwriting_signature():
    agent = RAGAgent.__new__(RAGAgent)
    assert callable(agent.ingest_text)
    assert callable(agent.get_ingested_hashes)


def test_get_ingested_hashes_missing_collection_returns_empty(tmp_path):
    config = RAGConfig()
    config.parent_store.path = tmp_path / "parents"
    db = MagicMock()
    db.collection_exists.return_value = False
    ingester = RAGIngester(config, db)
    assert ingester.get_ingested_hashes("notes") == set()
    db.get_collection.assert_not_called()


def test_ingest_text_standalone_splits_and_adds_chunks(tmp_path):
    config = RAGConfig()
    config.parent_store.path = tmp_path / "parents"
    config.chunking.adaptive = False
    db = MagicMock()
    db.collection_exists.return_value = False

    with patch.object(RAGIngester, "embedder", create=True):
        ingester = RAGIngester(config, db)
        ingester.embedder = MagicMock()
        ingester.embedder.embed_texts.return_value = [[0.1, 0.2]]
        result = ingester.ingest_text("# Title\n\nHello world.", "notes")

    assert isinstance(result, IngestResult)
    assert result.collection == "notes"
    assert result.chunks_indexed >= 1
    db.create_collection.assert_called_once()
    db.add_documents.assert_called_once()


def test_ingest_text_parent_only_when_doc_id_set(tmp_path):
    config = RAGConfig()
    config.parent_store.path = tmp_path / "parents"
    db = MagicMock()
    db.collection_exists.return_value = True

    ingester = RAGIngester(config, db)
    ingester.embedder = MagicMock()
    result = ingester.ingest_text(
        "parent body",
        "notes",
        doc_id="handwriting:notes:root",
        metadata={"source_type": "handwriting"},
    )

    assert result.files_indexed == 1
    assert result.chunks_indexed == 0
    db.add_documents.assert_not_called()
    stored = list((tmp_path / "parents").rglob("*.json"))
    assert stored


def test_ingest_text_child_adds_one_chunk(tmp_path):
    config = RAGConfig()
    config.parent_store.path = tmp_path / "parents"
    db = MagicMock()
    db.collection_exists.return_value = True

    ingester = RAGIngester(config, db)
    ingester.embedder = MagicMock()
    ingester.embedder.embed_texts.return_value = [[0.0]]
    result = ingester.ingest_text(
        "child chunk",
        "notes",
        metadata={"parent_id": "handwriting:notes:root", "child_index": 0},
    )

    assert result.chunks_indexed == 1
    db.add_documents.assert_called_once()


def test_agent_ingest_text_delegates_to_ingester():
    agent = RAGAgent.__new__(RAGAgent)
    agent.config = RAGConfig()
    agent.db = MagicMock()
    fake_result = IngestResult(collection="notes", files_indexed=1, chunks_indexed=2)
    with patch("tools.rag.ingest.RAGIngester") as mock_cls:
        mock_cls.return_value.ingest_text.return_value = fake_result
        out = agent.ingest_text("hello", "notes", doc_id="id1", metadata={"k": "v"})
    assert out == fake_result
    mock_cls.return_value.ingest_text.assert_called_once_with(
        "hello", "notes", doc_id="id1", metadata={"k": "v"}
    )
