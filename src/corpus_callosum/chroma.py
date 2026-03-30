"""ChromaDB client factory."""

from __future__ import annotations

from typing import Any

import chromadb

from .config import Config


def create_chroma_client(config: Config) -> Any:
    mode = config.chroma.mode.lower()

    if mode == "http":
        return chromadb.HttpClient(
            host=config.chroma.host,
            port=config.chroma.port,
            ssl=config.chroma.ssl,
        )

    config.paths.chromadb_store.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.paths.chromadb_store))
