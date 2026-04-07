"""Summary tool configuration."""

from dataclasses import dataclass

from corpus_callosum.config.base import BaseConfig


@dataclass
class SummaryConfig(BaseConfig):
    """Summary tool configuration."""

    summary_length: str = "medium"  # short | medium | long
    include_keywords: bool = True
    include_outline: bool = True
    collection_prefix: str = "summaries"
    max_context_chars: int = 15000

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryConfig":
        """Create summary config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            SummaryConfig instance
        """
        # Get base config
        base_config = super().from_dict(data)

        # Get summary-specific config
        summary_data = data.get("summaries", {})

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            summary_length=summary_data.get("summary_length", "medium"),
            include_keywords=summary_data.get("include_keywords", True),
            include_outline=summary_data.get("include_outline", True),
            collection_prefix=summary_data.get("collection_prefix", "summaries"),
            max_context_chars=summary_data.get("max_context_chars", 15000),
        )
