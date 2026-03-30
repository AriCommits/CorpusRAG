"""Configuration loading for CorpusCallosum."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import os

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        "vault": "./vault",
        "chromadb_store": "./chroma_store",
    },
    "embedding": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
    },
    "model": {
        "endpoint": "http://localhost:11434/api/generate",
        "name": "llama3",
        "timeout_seconds": 120.0,
        "max_flashcard_context_chars": 12000,
    },
    "chunking": {
        "size": 500,
        "overlap": 50,
    },
    "retrieval": {
        "top_k_semantic": 10,
        "top_k_bm25": 10,
        "top_k_final": 5,
        "rrf_k": 60,
    },
    "server": {
        "host": "0.0.0.0",
        "port": 8080,
    },
    "chroma": {
        "mode": "persistent",
        "host": "localhost",
        "port": 8000,
        "ssl": False,
    },
}


@dataclass(frozen=True, slots=True)
class PathsConfig:
    vault: Path
    chromadb_store: Path


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    model: str


@dataclass(frozen=True, slots=True)
class ModelConfig:
    endpoint: str
    name: str
    timeout_seconds: float
    max_flashcard_context_chars: int


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    size: int
    overlap: int


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    top_k_semantic: int
    top_k_bm25: int
    top_k_final: int
    rrf_k: int


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class ChromaConfig:
    mode: str
    host: str
    port: int
    ssl: bool


@dataclass(frozen=True, slots=True)
class Config:
    paths: PathsConfig
    embedding: EmbeddingConfig
    model: ModelConfig
    chunking: ChunkingConfig
    retrieval: RetrievalConfig
    server: ServerConfig
    chroma: ChromaConfig
    config_path: Path

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        project_root: Path,
        config_path: Path,
    ) -> "Config":
        paths = data.get("paths", {})
        embedding = data.get("embedding", {})
        model = data.get("model", {})
        chunking = data.get("chunking", {})
        retrieval = data.get("retrieval", {})
        server = data.get("server", {})
        chroma = data.get("chroma", {})

        parsed = cls(
            paths=PathsConfig(
                vault=_resolve_path(paths.get("vault", "./vault"), project_root),
                chromadb_store=_resolve_path(
                    paths.get("chromadb_store", "./chroma_store"), project_root
                ),
            ),
            embedding=EmbeddingConfig(
                model=str(
                    embedding.get(
                        "model", DEFAULT_CONFIG["embedding"]["model"]
                    )
                )
            ),
            model=ModelConfig(
                endpoint=str(
                    model.get("endpoint", DEFAULT_CONFIG["model"]["endpoint"])
                ),
                name=str(model.get("name", DEFAULT_CONFIG["model"]["name"])),
                timeout_seconds=float(
                    model.get(
                        "timeout_seconds", DEFAULT_CONFIG["model"]["timeout_seconds"]
                    )
                ),
                max_flashcard_context_chars=int(
                    model.get(
                        "max_flashcard_context_chars",
                        DEFAULT_CONFIG["model"]["max_flashcard_context_chars"],
                    )
                ),
            ),
            chunking=ChunkingConfig(
                size=int(chunking.get("size", DEFAULT_CONFIG["chunking"]["size"])),
                overlap=int(
                    chunking.get("overlap", DEFAULT_CONFIG["chunking"]["overlap"])
                ),
            ),
            retrieval=RetrievalConfig(
                top_k_semantic=int(
                    retrieval.get(
                        "top_k_semantic", DEFAULT_CONFIG["retrieval"]["top_k_semantic"]
                    )
                ),
                top_k_bm25=int(
                    retrieval.get(
                        "top_k_bm25", DEFAULT_CONFIG["retrieval"]["top_k_bm25"]
                    )
                ),
                top_k_final=int(
                    retrieval.get(
                        "top_k_final", DEFAULT_CONFIG["retrieval"]["top_k_final"]
                    )
                ),
                rrf_k=int(
                    retrieval.get("rrf_k", DEFAULT_CONFIG["retrieval"]["rrf_k"])
                ),
            ),
            server=ServerConfig(
                host=str(server.get("host", DEFAULT_CONFIG["server"]["host"])),
                port=int(server.get("port", DEFAULT_CONFIG["server"]["port"])),
            ),
            chroma=ChromaConfig(
                mode=str(chroma.get("mode", DEFAULT_CONFIG["chroma"]["mode"])),
                host=str(chroma.get("host", DEFAULT_CONFIG["chroma"]["host"])),
                port=int(chroma.get("port", DEFAULT_CONFIG["chroma"]["port"])),
                ssl=bool(chroma.get("ssl", DEFAULT_CONFIG["chroma"]["ssl"])),
            ),
            config_path=config_path,
        )
        parsed.validate()
        return parsed

    def validate(self) -> None:
        if self.chunking.size <= 0:
            raise ValueError("chunking.size must be positive")
        if self.chunking.overlap < 0:
            raise ValueError("chunking.overlap cannot be negative")
        if self.chunking.overlap >= self.chunking.size:
            raise ValueError("chunking.overlap must be smaller than chunking.size")
        if self.retrieval.top_k_final <= 0:
            raise ValueError("retrieval.top_k_final must be positive")
        if self.retrieval.rrf_k <= 0:
            raise ValueError("retrieval.rrf_k must be positive")
        if self.server.port <= 0:
            raise ValueError("server.port must be positive")
        if self.chroma.mode.lower() not in {"persistent", "http"}:
            raise ValueError("chroma.mode must be 'persistent' or 'http'")
        if self.chroma.port <= 0:
            raise ValueError("chroma.port must be positive")


def _resolve_path(value: str | Path, project_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in updates.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _default_config_path() -> Path:
    return PROJECT_ROOT / "configs" / "corpus_callosum.yaml"


def load_config(path: str | Path | None = None) -> Config:
    config_path = Path(
        path
        or os.getenv("CORPUS_CALLOSUM_CONFIG", str(_default_config_path()))
    ).expanduser()
    if not config_path.is_absolute():
        config_path = (PROJECT_ROOT / config_path).resolve()

    merged_data = deepcopy(DEFAULT_CONFIG)

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as file:
            user_data = yaml.safe_load(file) or {}
        if not isinstance(user_data, dict):
            raise ValueError(f"Config file must contain a mapping: {config_path}")
        merged_data = _deep_merge(merged_data, user_data)

    return Config.from_dict(
        merged_data, project_root=PROJECT_ROOT, config_path=config_path
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()
