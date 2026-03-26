# src/homeschool/config.py
from __future__ import annotations

import os
import secrets
from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml

REPO_ROOT   = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
DEFAULT_MANIFEST_DIR = Path.home() / ".sovereign_brain" / "manifest"


class ConfigError(Exception):
    pass


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _resolve_env_vars(obj: Any) -> Any:
    """
    Recursively walk config and substitute $ENV_VAR references in strings.
    Allows users to write:  vault: "$OBSIDIAN_VAULT_PATH"
    """
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(i) for i in obj]
    return obj


@lru_cache(maxsize=1)
def load() -> "Config":
    if not CONFIG_PATH.exists():
        raise ConfigError(
            f"config.yaml not found at {CONFIG_PATH}\n"
            "Copy config.yaml.example to config.yaml and fill in your values."
        )
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    raw = _resolve_env_vars(raw)
    return Config(raw)


class Config:
    def __init__(self, data: dict):
        self._data = data
        self._validate()

    def _validate(self):
        errors = []

        vault = self.paths.vault
        if vault == Path("/path/to/your/obsidian/vault"):
            errors.append("paths.vault has not been set in config.yaml")

        model_store = self.paths.model_store
        if model_store == Path("/path/to/your/ModelStore"):
            errors.append("paths.model_store has not been set in config.yaml")

        if self.chromadb.auth_token == "CHANGE_ME":
            errors.append(
                "chromadb.auth_token is still the default.\n"
                "  Generate one with: "
                "python3 -c \"import secrets; print(secrets.token_hex(32))\""
            )

        if self.hardware.gpu not in ("cpu", "nvidia", "metal"):
            errors.append(
                f"hardware.gpu must be one of: cpu, nvidia, metal "
                f"(got '{self.hardware.gpu}')"
            )

        if errors:
            raise ConfigError(
                "Invalid config.yaml:\n" +
                "\n".join(f"  • {e}" for e in errors)
            )

    # ── Accessors (typed, IDE-friendly) ───────────────────────

    @property
    def hardware(self) -> "HardwareConfig":
        return HardwareConfig(self._data["hardware"])

    @property
    def network(self) -> "NetworkConfig":
        return NetworkConfig(self._data["network"])

    @property
    def paths(self) -> "PathsConfig":
        return PathsConfig(self._data["paths"])

    @property
    def embedding(self) -> "EmbeddingConfig":
        return EmbeddingConfig(self._data["embedding"])

    @property
    def chromadb(self) -> "ChromaConfig":
        return ChromaConfig(self._data["chromadb"])

    @property
    def sync(self) -> "SyncConfig":
        return SyncConfig(self._data["sync"])

    @property
    def jan(self) -> "JanConfig":
        return JanConfig(self._data["jan"])


class HardwareConfig:
    def __init__(self, d: dict):
        self.gpu: str = d["gpu"]

    @property
    def is_nvidia(self) -> bool:
        return self.gpu == "nvidia"

    @property
    def is_metal(self) -> bool:
        return self.gpu == "metal"

    @property
    def gpu_layers(self) -> int:
        # Metal can't GPU-accelerate inside Docker, caller handles this
        return -1 if self.gpu == "nvidia" else 0


class NetworkConfig:
    def __init__(self, d: dict):
        self.bind_host: str  = d["bind_host"]
        self.ports:     dict = d["ports"]

    def chroma_url(self, from_container: bool = False) -> str:
        # Containers reach each other by service name, not localhost
        host = "chromadb" if from_container else self.bind_host
        return f"http://{host}:{self.ports['chromadb']}"


class PathsConfig:
    def __init__(self, d: dict):
        self.vault:        Path = Path(d["vault"])
        self.model_store:  Path = Path(d["model_store"])
        self.manifest_dir: Path = (
            Path(d["manifest_dir"]) if d.get("manifest_dir")
            else DEFAULT_MANIFEST_DIR
        )

    @property
    def embed_model(self) -> Path:
        from src.homeschool.config import load
        cfg = load()
        return self.model_store / cfg.embedding.model_file


class EmbeddingConfig:
    def __init__(self, d: dict):
        self.model_file:    str       = d["model_file"]
        self.n_ctx:         int       = d["n_ctx"]
        self.n_gpu_layers:  int       = d["n_gpu_layers"]
        self.split_headers: list      = d["split_headers"]
        self.batch_size:    int       = d.get("embed_batch_size", 32)


class ChromaConfig:
    def __init__(self, d: dict):
        self.collection_name:  str = d["collection_name"]
        self.distance_metric:  str = d["distance_metric"]
        self.auth_token:       str = d["auth_token"]


class SyncConfig:
    def __init__(self, d: dict):
        self.exclude_patterns: list[str] = d["exclude_patterns"]
        self.prune_deleted:    bool      = d["prune_deleted"]
        self.embed_batch_size: int       = d["embed_batch_size"]


class JanConfig:
    def __init__(self, d: dict):
        self.base_url:        str = d["base_url"]
        self.inference_model: str = d["inference_model"]
        self.embedding_model: str = d["embedding_model"]