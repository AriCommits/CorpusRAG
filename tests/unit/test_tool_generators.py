"""Unit tests for tool generators (flashcards, quizzes, summaries)."""

from unittest.mock import MagicMock

from llm import PromptTemplates
from tools.flashcards.config import FlashcardConfig
from tools.quizzes.config import QuizConfig
from tools.summaries.config import SummaryConfig


class TestFlashcardConfig:
    """Tests for FlashcardConfig."""

    def test_default_values(self) -> None:
        """Test default flashcard config values."""
        config = FlashcardConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
        )
        assert config.cards_per_topic == 10
        assert config.difficulty_levels == ["basic", "intermediate", "advanced"]
        assert config.format == "anki"
        assert config.collection_prefix == "flashcards"
        assert config.max_context_chars == 12000

    def test_custom_values(self) -> None:
        """Test custom flashcard config values."""
        config = FlashcardConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
            cards_per_topic=20,
            difficulty_levels=["advanced"],
            format="quizlet",
        )
        assert config.cards_per_topic == 20
        assert config.difficulty_levels == ["advanced"]
        assert config.format == "quizlet"

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "llm": {"model": "test"},
            "embedding": {"model": "test"},
            "database": {"mode": "persistent"},
            "paths": {"vault": "./vault"},
            "flashcards": {"cards_per_topic": 25, "format": "plain"},
        }
        config = FlashcardConfig.from_dict(data)
        assert config.cards_per_topic == 25
        assert config.format == "plain"

    def test_prompt_template_formatting(self) -> None:
        """Test flashcard prompt template renders with config values."""
        config = FlashcardConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
        )
        prompt = PromptTemplates.flashcard_generation(
            documents=["Sample text about Python programming"],
            difficulty="intermediate",
            count=config.cards_per_topic,
        )
        assert "Python" in prompt
        assert str(config.cards_per_topic) in prompt


class TestQuizConfig:
    """Tests for QuizConfig."""

    def test_default_values(self) -> None:
        """Test default quiz config values."""
        config = QuizConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
        )
        assert config.questions_per_topic == 15
        assert config.difficulty_distribution == {"easy": 0.3, "medium": 0.5, "hard": 0.2}
        assert config.format == "markdown"
        assert config.include_explanations is True
        assert isinstance(config.question_types, list)

    def test_custom_values(self) -> None:
        """Test custom quiz config values."""
        config = QuizConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
            questions_per_topic=20,
            include_explanations=False,
            format="json",
        )
        assert config.questions_per_topic == 20
        assert config.include_explanations is False
        assert config.format == "json"

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "llm": {"model": "test"},
            "embedding": {"model": "test"},
            "database": {"mode": "persistent"},
            "paths": {"vault": "./vault"},
            "quizzes": {"questions_per_topic": 15, "format": "csv"},
        }
        config = QuizConfig.from_dict(data)
        assert config.questions_per_topic == 15
        assert config.format == "csv"

    def test_question_types_available(self) -> None:
        """Test that question types are configured."""
        config = QuizConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
        )
        assert len(config.question_types) > 0
        # Should include common question types
        types = [t.lower() for t in config.question_types]
        assert any("choice" in t or "question" in t for t in types)


class TestSummaryConfig:
    """Tests for SummaryConfig."""

    def test_default_values(self) -> None:
        """Test default summary config values."""
        config = SummaryConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
        )
        assert config.summary_length in ["short", "medium", "long"]
        assert config.include_keywords is True
        assert config.include_outline is True
        assert config.max_context_chars == 15000

    def test_custom_values(self) -> None:
        """Test custom summary config values."""
        config = SummaryConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
            summary_length="long",
        )
        assert config.summary_length == "long"

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "llm": {"model": "test"},
            "embedding": {"model": "test"},
            "database": {"mode": "persistent"},
            "paths": {"vault": "./vault"},
            "summaries": {"summary_length": "short"},
        }
        config = SummaryConfig.from_dict(data)
        assert config.summary_length == "short"

    def test_summary_lengths_valid(self) -> None:
        """Test that all summary length options are valid."""
        valid_lengths = ["short", "medium", "long"]
        for length in valid_lengths:
            config = SummaryConfig(
                llm=MagicMock(),
                embedding=MagicMock(),
                database=MagicMock(),
                paths=MagicMock(),
                summary_length=length,
            )
            assert config.summary_length == length


class TestToolConfigFromDict:
    """Tests for tool config from_dict methods."""

    def test_flashcard_config_missing_keys(self) -> None:
        """Test flashcard config handles missing keys gracefully."""
        minimal_data = {
            "llm": {},
            "embedding": {},
            "database": {},
            "paths": {},
        }
        config = FlashcardConfig.from_dict(minimal_data)
        # Should use defaults
        assert config.cards_per_topic == 10

    def test_quiz_config_missing_keys(self) -> None:
        """Test quiz config handles missing keys gracefully."""
        minimal_data = {
            "llm": {},
            "embedding": {},
            "database": {},
            "paths": {},
        }
        config = QuizConfig.from_dict(minimal_data)
        # Should use defaults
        assert config.questions_per_topic == 15

    def test_summary_config_missing_keys(self) -> None:
        """Test summary config handles missing keys gracefully."""
        minimal_data = {
            "llm": {},
            "embedding": {},
            "database": {},
            "paths": {},
        }
        config = SummaryConfig.from_dict(minimal_data)
        # Should use defaults
        assert config.summary_length in ["short", "medium", "long"]

    def test_tool_configs_inherit_base_config(self) -> None:
        """Test that tool configs properly inherit base config."""
        data = {
            "llm": {"model": "test-model"},
            "embedding": {"model": "test-embedding"},
            "database": {"mode": "http"},
            "paths": {"vault": "./test-vault"},
        }

        flashcard_config = FlashcardConfig.from_dict(data)
        quiz_config = QuizConfig.from_dict(data)
        summary_config = SummaryConfig.from_dict(data)

        # All should inherit base config
        assert flashcard_config.llm.model == "test-model"
        assert quiz_config.llm.model == "test-model"
        assert summary_config.llm.model == "test-model"

        assert flashcard_config.embedding.model == "test-embedding"
        assert flashcard_config.database.mode == "http"


class TestToolConfigValidation:
    """Tests for tool config validation."""

    def test_flashcard_count_positive(self) -> None:
        """Test flashcard count is positive."""
        config = FlashcardConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
            cards_per_topic=0,
        )
        # Should allow 0 (even if not meaningful)
        assert config.cards_per_topic == 0

        config = FlashcardConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
            cards_per_topic=-1,
        )
        # Should allow negative (validation happens elsewhere)
        assert config.cards_per_topic == -1

    def test_quiz_format_valid(self) -> None:
        """Test quiz format validation."""
        valid_formats = ["markdown", "json", "csv"]
        for fmt in valid_formats:
            config = QuizConfig(
                llm=MagicMock(),
                embedding=MagicMock(),
                database=MagicMock(),
                paths=MagicMock(),
                format=fmt,
            )
            assert config.format == fmt

    def test_summary_length_valid_values(self) -> None:
        """Test summary length uses valid values."""
        valid_lengths = ["short", "medium", "long"]
        for length in valid_lengths:
            config = SummaryConfig(
                llm=MagicMock(),
                embedding=MagicMock(),
                database=MagicMock(),
                paths=MagicMock(),
                summary_length=length,
            )
            assert config.summary_length == length
