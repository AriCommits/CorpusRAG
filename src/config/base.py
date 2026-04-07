"""Base configuration dataclasses for CorpusCallosum."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from corpus_callosum.llm import LLMConfig as LLMBackendConfig


@dataclass
class LLMConfig:
    """Shared LLM configuration with enhanced backend support."""

    # Legacy fields for compatibility
    endpoint: str = "http://localhost:11434"
    model: str = "llama3"
    timeout_seconds: float = 120.0
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    # New backend configuration
    backend: str = "ollama"
    api_key: Optional[str] = None
    fallback_models: list[str] = field(default_factory=list)
    
    def to_backend_config(self) -> LLMBackendConfig:
        """Convert to LLM backend configuration."""
        return LLMBackendConfig.from_dict({
            "backend": self.backend,
            "endpoint": self.endpoint,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "api_key": self.api_key,
            "fallback_models": self.fallback_models,
        })


@dataclass
class EmbeddingConfig:
    """Shared embedding configuration."""

    backend: str = "ollama"  # ollama | sentence-transformers
    model: str = "nomic-embed-text"
    dimensions: Optional[int] = None


@dataclass
class DatabaseConfig:
    """Shared database configuration."""

    backend: str = "chromadb"
    mode: str = "persistent"  # persistent | http
    host: str = "localhost"
    port: int = 8000
    persist_directory: Path = field(default_factory=lambda: Path("./chroma_store"))


@dataclass
class PathsConfig:
    """Shared paths configuration."""

    vault: Path = field(default_factory=lambda: Path("./vault"))
    scratch_dir: Path = field(default_factory=lambda: Path("./scratch"))
    output_dir: Path = field(default_factory=lambda: Path("./output"))


@dataclass
class BaseConfig:
    """Base configuration inherited by all tools."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "BaseConfig":
        """Create config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            BaseConfig instance
        """
        llm_data = data.get("llm", {})
        embedding_data = data.get("embedding", {})
        database_data = data.get("database", {})
        paths_data = data.get("paths", {})

        # Convert string paths to Path objects
        if "persist_directory" in database_data and isinstance(
            database_data["persist_directory"], str
        ):
            database_data["persist_directory"] = Path(database_data["persist_directory"])

        for key in ["vault", "scratch_dir", "output_dir"]:
            if key in paths_data and isinstance(paths_data[key], str):
                paths_data[key] = Path(paths_data[key])

        return cls(
            llm=LLMConfig(**llm_data),
            embedding=EmbeddingConfig(**embedding_data),
            database=DatabaseConfig(**database_data),
            paths=PathsConfig(**paths_data),
        )

    def to_dict(self) -> dict:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of config
        """
        return {
            "llm": {
                "endpoint": self.llm.endpoint,
                "model": self.llm.model,
                "timeout_seconds": self.llm.timeout_seconds,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "backend": self.llm.backend,
                "api_key": self.llm.api_key,
                "fallback_models": self.llm.fallback_models,
            },
            "embedding": {
                "backend": self.embedding.backend,
                "model": self.embedding.model,
                "dimensions": self.embedding.dimensions,
            },
            "database": {
                "backend": self.database.backend,
                "mode": self.database.mode,
                "host": self.database.host,
                "port": self.database.port,
                "persist_directory": str(self.database.persist_directory),
            },
            "paths": {
                "vault": str(self.paths.vault),
                "scratch_dir": str(self.paths.scratch_dir),
                "output_dir": str(self.paths.output_dir),
            },
        }
