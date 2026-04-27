"""Shared utilities for MCP server tool implementations."""

from pathlib import Path

from config import load_config
from config.base import BaseConfig
from db import ChromaDBBackend
from utils.security import SecurityError
from utils.validation import get_validator


def init_config(config_path: str | None = None) -> BaseConfig:
    """Load configuration from YAML, defaulting to configs/base.yaml."""
    path = Path(config_path) if config_path else Path("configs/base.yaml")
    return load_config(str(path))


def init_db(config: BaseConfig) -> ChromaDBBackend:
    """Create ChromaDB backend from config."""
    return ChromaDBBackend(config.database)


def validate_query(query: str) -> str:
    """Validate query string, raising ValueError on security violations."""
    try:
        return get_validator().validate_query(query)
    except SecurityError as e:
        raise ValueError(str(e)) from e


def validate_collection(name: str) -> str:
    """Validate collection name, raising ValueError on security violations."""
    try:
        return get_validator().validate_collection_name(name)
    except SecurityError as e:
        raise ValueError(str(e)) from e


def validate_top_k(top_k: int, min_val: int = 1, max_val: int = 100) -> int:
    """Validate top_k parameter, raising ValueError on security violations."""
    try:
        return get_validator().validate_top_k(top_k, min_val=min_val, max_val=max_val)
    except SecurityError as e:
        raise ValueError(str(e)) from e
