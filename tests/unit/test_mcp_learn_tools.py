"""Tests for mcp_server/tools/learn.py learning tool functions."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

LEARN_MODULE_PATH = Path(__file__).parents[2] / "src" / "mcp_server" / "tools" / "learn.py"


def _load_learn_module():
    """Load learn.py directly by file path, bypassing mcp_server package init."""
    spec = importlib.util.spec_from_file_location("mcp_server.tools.learn", LEARN_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_config(tmp_path):
    """Create a minimal config yaml and return a loaded BaseConfig."""
    cfg_file = tmp_path / "base.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "llm": {"model": "test-model"},
                "database": {"mode": "persistent", "persist_directory": str(tmp_path)},
            }
        )
    )
    from config import load_config

    return load_config(cfg_file)


@pytest.fixture
def mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# TestGenerateFlashcards
# ---------------------------------------------------------------------------


class TestGenerateFlashcards:
    def test_missing_generators_returns_error(self, tmp_config, mock_db):
        """When GENERATORS_AVAILABLE is False, return error dict mentioning 'generators'."""
        fake_fc_module = MagicMock()
        fake_fc_module.GENERATORS_AVAILABLE = False

        saved = sys.modules.get("tools.flashcards")
        sys.modules["tools.flashcards"] = fake_fc_module
        try:
            learn = _load_learn_module()
            result = learn.generate_flashcards("notes", 10, "medium", tmp_config, mock_db)
        finally:
            if saved is None:
                sys.modules.pop("tools.flashcards", None)
            else:
                sys.modules["tools.flashcards"] = saved

        assert result["status"] == "error"
        assert "generators" in result["error"]

    def test_returns_dict_structure(self, tmp_config, mock_db):
        """When generators available, returns dict with expected keys on success."""
        fake_cards = [{"front": "Q1", "back": "A1"}]

        fake_config_instance = MagicMock()
        fake_config_cls = MagicMock()
        fake_config_cls.from_dict = MagicMock(return_value=fake_config_instance)

        fake_generator_instance = MagicMock()
        fake_generator_instance.generate.return_value = fake_cards
        fake_generator_cls = MagicMock(return_value=fake_generator_instance)

        fake_fc_module = MagicMock()
        fake_fc_module.GENERATORS_AVAILABLE = True
        fake_fc_module.FlashcardConfig = fake_config_cls
        fake_fc_module.FlashcardGenerator = fake_generator_cls

        fake_validator = MagicMock()
        fake_validator.validate_collection_name.return_value = "notes"
        fake_validation_module = MagicMock()
        fake_validation_module.get_validator.return_value = fake_validator

        saved_fc = sys.modules.get("tools.flashcards")
        saved_val = sys.modules.get("utils.validation")
        sys.modules["tools.flashcards"] = fake_fc_module
        sys.modules["utils.validation"] = fake_validation_module
        try:
            learn = _load_learn_module()
            result = learn.generate_flashcards("notes", 10, "medium", tmp_config, mock_db)
        finally:
            if saved_fc is None:
                sys.modules.pop("tools.flashcards", None)
            else:
                sys.modules["tools.flashcards"] = saved_fc
            if saved_val is None:
                sys.modules.pop("utils.validation", None)
            else:
                sys.modules["utils.validation"] = saved_val

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "flashcards" in result
        assert "collection" in result
        assert "count" in result
        fake_generator_instance.generate.assert_called_once_with(
            "notes", difficulty="medium", count=10
        )
        fake_config_cls.from_dict.assert_called_once()
        passed = fake_config_cls.from_dict.call_args.args[0]
        assert passed == (tmp_config.raw or tmp_config.to_dict())


# ---------------------------------------------------------------------------
# TestGenerateSummary
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    def test_returns_dict_structure(self, tmp_config, mock_db):
        fake_summary = {"summary": "A summary.", "keywords": []}

        fake_config_instance = MagicMock()
        fake_config_cls = MagicMock()
        fake_config_cls.from_dict = MagicMock(return_value=fake_config_instance)

        fake_generator_instance = MagicMock()
        fake_generator_instance.generate.return_value = fake_summary
        fake_generator_cls = MagicMock(return_value=fake_generator_instance)

        fake_sm_module = MagicMock()
        fake_sm_module.GENERATORS_AVAILABLE = True
        fake_sm_module.SummaryConfig = fake_config_cls
        fake_sm_module.SummaryGenerator = fake_generator_cls

        saved = sys.modules.get("tools.summaries")
        sys.modules["tools.summaries"] = fake_sm_module
        try:
            learn = _load_learn_module()
            fake_corpus = MagicMock()
            fake_corpus.summarize.return_value = fake_summary
            with patch("kernel.Corpus.from_loaded", return_value=fake_corpus):
                result = learn.generate_summary(
                    "notes", "machine learning", "medium", tmp_config, mock_db
                )
        finally:
            if saved is None:
                sys.modules.pop("tools.summaries", None)
            else:
                sys.modules["tools.summaries"] = saved

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "summary" in result
        assert "collection" in result
        assert "topic" in result


# ---------------------------------------------------------------------------
# TestGenerateQuiz
# ---------------------------------------------------------------------------


class TestGenerateQuiz:
    def test_returns_dict_structure(self, tmp_config, mock_db):
        fake_quiz = [{"question": "Q?", "answer": "A"}]

        fake_config_instance = MagicMock()
        fake_config_cls = MagicMock()
        fake_config_cls.from_dict = MagicMock(return_value=fake_config_instance)

        fake_generator_instance = MagicMock()
        fake_generator_instance.generate.return_value = fake_quiz
        fake_generator_cls = MagicMock(return_value=fake_generator_instance)

        fake_qz_module = MagicMock()
        fake_qz_module.GENERATORS_AVAILABLE = True
        fake_qz_module.QuizConfig = fake_config_cls
        fake_qz_module.QuizGenerator = fake_generator_cls

        saved = sys.modules.get("tools.quizzes")
        sys.modules["tools.quizzes"] = fake_qz_module
        try:
            learn = _load_learn_module()
            result = learn.generate_quiz("notes", 5, None, tmp_config, mock_db)
        finally:
            if saved is None:
                sys.modules.pop("tools.quizzes", None)
            else:
                sys.modules["tools.quizzes"] = saved

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "quiz" in result
        assert "collection" in result
        assert "count" in result
        fake_generator_instance.generate.assert_called_once_with("notes", count=5)


# ---------------------------------------------------------------------------
# TestCleanTranscript
# ---------------------------------------------------------------------------


class TestTranscribeVideo:
    def test_uses_real_transcriber_signature(self, tmp_config, mock_db, tmp_path):
        video_file = tmp_path / "lecture.mp4"
        video_file.write_bytes(b"fake")

        fake_video_config_instance = MagicMock()
        fake_video_config_cls = MagicMock()
        fake_video_config_cls.from_dict = MagicMock(return_value=fake_video_config_instance)

        fake_transcriber_instance = MagicMock()
        fake_transcriber_instance.transcribe_file.return_value = "hello world"
        fake_transcriber_cls = MagicMock(return_value=fake_transcriber_instance)

        fake_video_module = MagicMock()
        fake_video_module.VideoConfig = fake_video_config_cls
        fake_video_module.VideoTranscriber = fake_transcriber_cls

        saved = sys.modules.get("tools.video")
        sys.modules["tools.video"] = fake_video_module
        try:
            learn = _load_learn_module()
            result = learn.transcribe_video(str(video_file), "notes", "base", tmp_config, mock_db)
        finally:
            if saved is None:
                sys.modules.pop("tools.video", None)
            else:
                sys.modules["tools.video"] = saved

        assert result["status"] == "success"
        assert result["transcript"] == "hello world"
        fake_transcriber_cls.assert_called_once_with(fake_video_config_instance)
        transcribe_args = fake_transcriber_instance.transcribe_file.call_args.args
        assert len(transcribe_args) == 1
        assert Path(transcribe_args[0]) == video_file


class TestCleanTranscript:
    def test_returns_dict_structure(self, tmp_config):
        fake_video_config_instance = MagicMock()
        fake_video_config_cls = MagicMock()
        fake_video_config_cls.from_dict = MagicMock(return_value=fake_video_config_instance)

        fake_cleaner_instance = MagicMock()
        fake_cleaner_instance.clean.return_value = "Cleaned text."
        fake_cleaner_cls = MagicMock(return_value=fake_cleaner_instance)

        fake_video_module = MagicMock()
        fake_video_module.VideoConfig = fake_video_config_cls
        fake_video_module.TranscriptCleaner = fake_cleaner_cls

        saved = sys.modules.get("tools.video")
        sys.modules["tools.video"] = fake_video_module
        try:
            learn = _load_learn_module()
            result = learn.clean_transcript("raw text", None, tmp_config)
        finally:
            if saved is None:
                sys.modules.pop("tools.video", None)
            else:
                sys.modules["tools.video"] = saved

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "cleaned_transcript" in result


# ---------------------------------------------------------------------------
# TestNoFastapiImports
# ---------------------------------------------------------------------------


class TestNoFastapiImports:
    def test_no_fastapi_in_module(self):
        """learn.py must not import fastapi."""
        source = LEARN_MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "fastapi" not in alias.name.lower(), (
                        f"Found fastapi import: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "fastapi" not in module.lower(), f"Found fastapi import from: {module}"
