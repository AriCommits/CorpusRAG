"""Tests for the Corpus kernel facade."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from kernel import Corpus
from tools.rag.config import RAGConfig
from tools.rag.ingest import IngestResult


def _rag_config(tmp_path: Path) -> RAGConfig:
    cfg = RAGConfig()
    cfg.parent_store.path = tmp_path / "parents"
    cfg.database.persist_directory = tmp_path / "chroma"
    cfg.raw = {"llm": {"model": "test"}, "summaries": {"summary_length": "short"}}
    return cfg


def test_from_config_path_loads_persistent_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "base.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "llm": {"model": "test-model"},
                "database": {
                    "mode": "persistent",
                    "persist_directory": str(tmp_path / "chroma"),
                },
                "paths": {"vault": str(tmp_path / "vault")},
            }
        ),
        encoding="utf-8",
    )
    corpus = Corpus.from_config_path(cfg_file)
    assert isinstance(corpus, Corpus)
    assert corpus.config.database.mode == "persistent"
    assert corpus.config.llm.model == "test-model"


def test_ingest_text_uses_user_facing_collection(tmp_path: Path) -> None:
    db = MagicMock()
    db.collection_exists.return_value = False
    corpus = Corpus(_rag_config(tmp_path), db)

    with patch("tools.rag.ingest.RAGIngester.embedder", create=True):
        with patch("tools.rag.agent.RAGAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.ingest_text.return_value = IngestResult("notes", 1, 1)
            mock_agent_cls.return_value = mock_agent
            result = corpus.ingest_text("hello world", "notes")

    mock_agent.ingest_text.assert_called_once_with(
        "hello world", "notes", doc_id=None, metadata=None
    )
    assert result.collection == "notes"


def test_sample_delegates_to_generation_helper(tmp_path: Path) -> None:
    db = MagicMock()
    corpus = Corpus(_rag_config(tmp_path), db)
    with patch("tools.generation.sample_documents", return_value=["passage"]) as sample:
        texts = corpus.sample("notes", query="overview", n=3)
    sample.assert_called_once()
    assert sample.call_args.kwargs["query_text"] == "overview"
    assert sample.call_args.kwargs["n_results"] == 3
    assert sample.call_args.args[2] == "notes"
    assert texts == ["passage"]


def test_ask_passes_user_facing_collection(tmp_path: Path) -> None:
    db = MagicMock()
    corpus = Corpus(_rag_config(tmp_path), db)
    with patch("tools.rag.agent.RAGAgent") as mock_agent_cls:
        mock_agent_cls.return_value.query.return_value = "because notes say so"
        answer = corpus.ask("What is X?", "notes", top_k=4)
    mock_agent_cls.return_value.query.assert_called_once_with("What is X?", "notes", top_k=4)
    assert answer == "because notes say so"


def test_summarize_uses_summary_generator(tmp_path: Path) -> None:
    db = MagicMock()
    corpus = Corpus(_rag_config(tmp_path), db)
    fake = {"summary": "A short summary.", "collection": "notes"}
    with patch("tools.summaries.SummaryGenerator") as mock_gen_cls:
        mock_gen_cls.return_value.generate.return_value = fake
        result = corpus.summarize("notes", topic="intro", length="short")
    mock_gen_cls.return_value.generate.assert_called_once_with("notes", "intro")
    assert result["summary"] == "A short summary."


def test_complete_delegates_to_generation_helper(tmp_path: Path) -> None:
    db = MagicMock()
    corpus = Corpus(_rag_config(tmp_path), db)
    with patch("tools.generation.complete_prompt", return_value="ok") as complete:
        assert corpus.complete("hello") == "ok"
    complete.assert_called_once()
    assert complete.call_args.args[1] == "hello"
