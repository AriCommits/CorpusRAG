"""Quiz tool configuration."""

from typing import Any

from pydantic import Field

from config.base import BaseConfig


class QuizConfig(BaseConfig):
    """Quiz tool configuration."""

    questions_per_topic: int = 15
    question_types: list[str] = Field(
        default_factory=lambda: ["multiple_choice", "true_false", "short_answer"]
    )
    difficulty_distribution: dict[str, float] = Field(
        default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )
    format: str = "markdown"  # markdown | json | csv
    include_explanations: bool = True
    collection_prefix: str = "rag"
    max_context_chars: int = 12000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuizConfig":
        """Create quizconfig from dictionary."""
        base_config, tool_data = BaseConfig.split_section(data, "quizzes")
        merged = base_config.model_dump(exclude={"raw"})
        merged.update(tool_data)

        # Preserve specific backward-compatibility logic for video
        if "quizzes" == "video":
            if "clean_ollama_host" not in merged:
                merged["clean_ollama_host"] = base_config.llm.endpoint

        inst = cls.model_validate(merged)
        inst.raw = data
        return inst
