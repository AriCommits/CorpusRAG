"""Base configuration models for CorpusRAG."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from llm import LLMConfig as LLMBackendConfig


class LLMConfig(BaseModel):
    """Shared LLM configuration with enhanced backend support."""

    model_config = ConfigDict(extra="ignore")

    # Legacy fields for compatibility
    endpoint: str = "http://localhost:11434"
    model: str = "gemma4:26b-a4b-it-q4_K_M"
    timeout_seconds: float = 120.0
    temperature: float = 0.7
    max_tokens: int | None = None

    # New backend configuration
    backend: str = "ollama"
    api_key: str | None = None
    fallback_models: list[str] = Field(default_factory=list)

    # Rate limiting configuration
    rate_limit_rpm: int | None = None
    rate_limit_concurrent: int | None = None

    def to_backend_config(self) -> LLMBackendConfig:
        """Convert to LLM backend configuration."""
        return LLMBackendConfig.from_dict(
            {
                "backend": self.backend,
                "endpoint": self.endpoint,
                "model": self.model,
                "timeout_seconds": self.timeout_seconds,
                "api_key": self.api_key,
                "fallback_models": self.fallback_models,
            }
        )


class EmbeddingConfig(BaseModel):
    """Shared embedding configuration."""

    model_config = ConfigDict(extra="ignore")

    backend: str = "ollama"  # ollama | sentence-transformers
    model: str = "embeddinggemma"
    dimensions: int | None = None


class DatabaseConfig(BaseModel):
    """Shared database configuration."""

    model_config = ConfigDict(extra="ignore")

    backend: str = "chromadb"
    mode: str = "persistent"  # persistent | http
    host: str = "localhost"
    port: int = 8000
    persist_directory: Path = Field(default_factory=lambda: Path("./chroma_store"))


class PathsConfig(BaseModel):
    """Shared paths configuration."""

    model_config = ConfigDict(extra="ignore")

    vault: Path = Field(default_factory=lambda: Path("./vault"))
    scratch_dir: Path = Field(default_factory=lambda: Path("./scratch"))
    output_dir: Path = Field(default_factory=lambda: Path("./output"))


class BaseConfig(BaseModel):
    """Base configuration inherited by all tools."""

    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    # Full unmodeled configuration dictionary as loaded.
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseConfig":
        """Create config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            BaseConfig instance
        """
        inst = cls.model_validate(data)
        inst.raw = data
        return inst

    @classmethod
    def split_section(
        cls, data: dict[str, Any], section: str
    ) -> tuple["BaseConfig", dict[str, Any]]:
        """Return ``(base, section_dict)`` for tool config ``from_dict`` helpers."""
        return cls.from_dict(data), dict(data.get(section) or {})

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseConfig):
            return self.model_dump() == other.model_dump()
        return super().__eq__(other)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of config
        """
        # Dump using mode="json" so Paths become strings, keeping it
        # structurally identical to the old dataclass output.
        data = self.model_dump(mode="json")

        # Keep API key masking logic from the previous to_dict
        if "llm" in data and "api_key" in data["llm"] and data["llm"]["api_key"] is not None:
            data["llm"]["api_key"] = "***"

        return data

    def save_to_yaml(self, path: Path) -> None:
        """Save the configuration back to a YAML file."""
        dumped = self.model_dump(mode="json", exclude={"raw"})
        # Merge updated core config back into the raw config to preserve tool settings
        final_data = self.raw.copy()
        final_data.update(dumped)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(final_data, f, default_flow_style=False, sort_keys=False)
