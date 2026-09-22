"""Flashcard tool configuration."""

from typing import Any

from pydantic import Field

from config.base import BaseConfig


class FlashcardConfig(BaseConfig):
    """Flashcard tool configuration."""

    cards_per_topic: int = 10
    difficulty_levels: list[str] = Field(
        default_factory=lambda: ["basic", "intermediate", "advanced"]
    )
    format: str = "anki"  # anki | quizlet | plain
    collection_prefix: str = "rag"
    max_context_chars: int = 12000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlashcardConfig":
        """Create flashcardconfig from dictionary."""
        base_config, tool_data = BaseConfig.split_section(data, "flashcards")
        merged = base_config.model_dump(exclude={"raw"})
        merged.update(tool_data)

        # Preserve specific backward-compatibility logic for video
        if "flashcards" == "video":
            if "clean_ollama_host" not in merged:
                merged["clean_ollama_host"] = base_config.llm.endpoint

        inst = cls.model_validate(merged)
        inst.raw = data
        return inst
