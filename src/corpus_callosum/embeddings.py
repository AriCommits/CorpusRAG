"""Embedding backends for CorpusCallosum.

Supports multiple embedding providers:
- sentence-transformers: Local HuggingFace models (default)
- ollama: Ollama embedding models (nomic-embed-text, mxbai-embed-large, etc.)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .config import Config


class EmbeddingBackendType(StrEnum):
    """Supported embedding backend types."""

    SENTENCE_TRANSFORMERS = "sentence-transformers"
    OLLAMA = "ollama"


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts into embeddings.

        Args:
            texts: List of strings to encode.

        Returns:
            List of embedding vectors (each is a list of floats).
        """


class SentenceTransformersBackend(EmbeddingBackend):
    """Embedding backend using sentence-transformers library."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts using sentence-transformers."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()


class OllamaEmbeddingBackend(EmbeddingBackend):
    """Embedding backend using Ollama's /api/embeddings endpoint."""

    def __init__(self, model_name: str, endpoint: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.endpoint = endpoint.rstrip("/")

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts using Ollama's embedding API."""
        embeddings = []
        url = f"{self.endpoint}/api/embeddings"

        for text in texts:
            response = httpx.post(
                url,
                json={"model": self.model_name, "prompt": text},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            embeddings.append(data["embedding"])

        return embeddings


def create_embedding_backend(config: Config) -> EmbeddingBackend:
    """Create an embedding backend from configuration.

    The backend is determined by the embedding.backend config value.
    If not specified, it's inferred from the model name:
    - Models starting with "sentence-transformers/" use sentence-transformers
    - Other models use Ollama

    Args:
        config: Application configuration.

    Returns:
        An EmbeddingBackend instance.
    """
    model_name = config.embedding.model
    backend_type = config.embedding.backend

    # Auto-detect backend if not specified
    if backend_type is None:
        if model_name.startswith("sentence-transformers/") or "/" not in model_name:
            # Assume HuggingFace model if it has sentence-transformers prefix
            # or if it's a simple name like "all-MiniLM-L6-v2"
            if not model_name.startswith("sentence-transformers/") and "/" not in model_name:
                # Check if it looks like an Ollama model (common Ollama embedding models)
                ollama_models = {
                    "nomic-embed-text",
                    "mxbai-embed-large",
                    "all-minilm",
                    "snowflake-arctic-embed",
                }
                if (
                    model_name.lower() in ollama_models
                    or model_name.split(":")[0].lower() in ollama_models
                ):
                    backend_type = EmbeddingBackendType.OLLAMA
                else:
                    backend_type = EmbeddingBackendType.SENTENCE_TRANSFORMERS
            else:
                backend_type = EmbeddingBackendType.SENTENCE_TRANSFORMERS
        else:
            # Assume Ollama for other model names (e.g., "nomic-embed-text")
            backend_type = EmbeddingBackendType.OLLAMA

    if backend_type == EmbeddingBackendType.OLLAMA:
        return OllamaEmbeddingBackend(
            model_name=model_name,
            endpoint=config.model.endpoint,  # Reuse LLM endpoint for Ollama
        )
    elif backend_type == EmbeddingBackendType.SENTENCE_TRANSFORMERS:
        return SentenceTransformersBackend(model_name=model_name)
    else:
        raise ValueError(f"Unknown embedding backend: {backend_type}")
