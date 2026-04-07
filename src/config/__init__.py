"""Configuration system for CorpusCallosum."""

from .base import BaseConfig, DatabaseConfig, EmbeddingConfig, LLMConfig, PathsConfig
from .loader import load_config, merge_configs

__all__ = [
    "BaseConfig",
    "DatabaseConfig",
    "EmbeddingConfig",
    "LLMConfig",
    "PathsConfig",
    "load_config",
    "merge_configs",
]
