"""Quiz tool configuration."""

from dataclasses import dataclass, field

from corpus_callosum.config.base import BaseConfig


@dataclass
class QuizConfig(BaseConfig):
    """Quiz tool configuration."""

    questions_per_topic: int = 15
    question_types: list[str] = field(
        default_factory=lambda: ["multiple_choice", "true_false", "short_answer"]
    )
    difficulty_distribution: dict[str, float] = field(
        default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )
    format: str = "markdown"  # markdown | json | csv
    include_explanations: bool = True
    collection_prefix: str = "quizzes"
    max_context_chars: int = 12000

    @classmethod
    def from_dict(cls, data: dict) -> "QuizConfig":
        """Create quiz config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            QuizConfig instance
        """
        # Get base config
        base_config = super().from_dict(data)

        # Get quiz-specific config
        quiz_data = data.get("quizzes", {})

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            questions_per_topic=quiz_data.get("questions_per_topic", 15),
            question_types=quiz_data.get(
                "question_types", ["multiple_choice", "true_false", "short_answer"]
            ),
            difficulty_distribution=quiz_data.get(
                "difficulty_distribution", {"easy": 0.3, "medium": 0.5, "hard": 0.2}
            ),
            format=quiz_data.get("format", "markdown"),
            include_explanations=quiz_data.get("include_explanations", True),
            collection_prefix=quiz_data.get("collection_prefix", "quizzes"),
            max_context_chars=quiz_data.get("max_context_chars", 12000),
        )
