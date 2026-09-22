"""Summary tool configuration."""

from typing import Any

from config.base import BaseConfig


class SummaryConfig(BaseConfig):
    """Summary tool configuration."""

    summary_length: str = "medium"  # short | medium | long
    include_keywords: bool = True
    include_outline: bool = True
    collection_prefix: str = "rag"
    max_context_chars: int = 15000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SummaryConfig":
        """Create summaryconfig from dictionary."""
        base_config, tool_data = BaseConfig.split_section(data, "summaries")
        merged = base_config.model_dump(exclude={"raw"})
        merged.update(tool_data)

        # Preserve specific backward-compatibility logic for video
        if "summaries" == "video":
            if "clean_ollama_host" not in merged:
                merged["clean_ollama_host"] = base_config.llm.endpoint

        inst = cls.model_validate(merged)
        inst.raw = data
        return inst
