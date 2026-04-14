"""Shared helpers for CLI commands."""

from pathlib import Path
from typing import TypeVar

from config import BaseConfig, load_config
from db import ChromaDBBackend

T = TypeVar("T", bound=BaseConfig)


def load_cli_config(config_path: str | Path, config_class: type[T] = BaseConfig) -> T:
    """Load a typed config object for CLI commands."""
    return load_config(Path(config_path), config_class=config_class)


def load_cli_db(
    config_path: str | Path, config_class: type[T] = BaseConfig
) -> tuple[T, ChromaDBBackend]:
    """Load config and initialize the configured Chroma backend."""
    cfg = load_cli_config(config_path, config_class=config_class)
    return cfg, ChromaDBBackend(cfg.database)
