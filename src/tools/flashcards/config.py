"""Flashcard tool configuration."""

from dataclasses import dataclass, field

from corpus_callosum.config.base import BaseConfig


@dataclass
class FlashcardConfig(BaseConfig):
    """Flashcard tool configuration."""

    cards_per_topic: int = 10
    difficulty_levels: list[str] = field(
        default_factory=lambda: ["basic", "intermediate", "advanced"]
    )
    format: str = "anki"  # anki | quizlet | plain
    collection_prefix: str = "flashcards"
    max_context_chars: int = 12000

    @classmethod
    def from_dict(cls, data: dict) -> "FlashcardConfig":
        """Create flashcard config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            FlashcardConfig instance
        """
        # Get base config
        base_config = super().from_dict(data)

        # Get flashcard-specific config
        flashcard_data = data.get("flashcards", {})

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            cards_per_topic=flashcard_data.get("cards_per_topic", 10),
            difficulty_levels=flashcard_data.get(
                "difficulty_levels", ["basic", "intermediate", "advanced"]
            ),
            format=flashcard_data.get("format", "anki"),
            collection_prefix=flashcard_data.get("collection_prefix", "flashcards"),
            max_context_chars=flashcard_data.get("max_context_chars", 12000),
        )
