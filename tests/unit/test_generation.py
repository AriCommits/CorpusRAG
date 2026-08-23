"""Tests for shared collection LLM generation helpers."""

from unittest.mock import MagicMock, patch

import pytest

from tools.flashcards.config import FlashcardConfig
from tools.generation import complete_prompt, full_collection_name, sample_documents
from tools.quizzes.generator import QuizGenerator


def test_full_collection_name_uses_rag_prefix():
    cfg = FlashcardConfig()
    assert full_collection_name(cfg, "notes") == "rag_notes"


def test_sample_documents_missing_collection():
    db = MagicMock()
    db.collection_exists.return_value = False
    with pytest.raises(ValueError, match="does not exist"):
        sample_documents(db, FlashcardConfig(), "notes", query_text="q", n_results=5)


def test_sample_documents_empty_collection():
    db = MagicMock()
    db.collection_exists.return_value = True
    db.query.return_value = {"documents": [[]]}
    with (
        patch("tools.generation.EmbeddingClient") as mock_embed,
        pytest.raises(ValueError, match="No documents found"),
    ):
        mock_embed.return_value.embed_query.return_value = [0.1]
        sample_documents(db, FlashcardConfig(), "notes", query_text="q", n_results=5)


def test_quiz_generator_does_not_pad_placeholders():
    from tools.quizzes.config import QuizConfig

    qcfg = QuizConfig()
    gen = QuizGenerator(qcfg, MagicMock())
    gen._generate_with_llm = MagicMock(  # type: ignore[method-assign]
        return_value=[{"question": "Only one", "type": "short_answer", "answer": "A"}]
    )
    with patch("tools.quizzes.generator.sample_documents", return_value=["doc"]):
        questions = gen.generate("notes", count=5)
    assert len(questions) == 1
    assert "Additional Question" not in questions[0]["question"]


def test_complete_prompt_returns_stripped_text():
    cfg = FlashcardConfig()
    fake_backend = MagicMock()
    fake_backend.complete.return_value = MagicMock(text="  hello  ")
    with patch("tools.generation.create_backend", return_value=fake_backend):
        assert complete_prompt(cfg, "prompt") == "hello"
    fake_backend.complete.assert_called_once_with("prompt")
