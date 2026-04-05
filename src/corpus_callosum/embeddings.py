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

    # Maximum token limit for most Ollama embedding models (conservative estimate)
    MAX_TOKENS = 512  # Most embedding models support 512-2048 tokens
    CHARS_PER_TOKEN = 4  # Rough estimate: 1 token ≈ 4 characters

    def __init__(self, model_name: str, endpoint: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.endpoint = endpoint.rstrip("/")
        self.max_chars = self.MAX_TOKENS * self.CHARS_PER_TOKEN

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts using Ollama's embedding API.

        Automatically truncates texts that exceed the model's context window.
        """
        embeddings = []
        url = f"{self.endpoint}/api/embeddings"

        for idx, text in enumerate(texts):
            # Truncate text if it's too long
            truncated_text = text[: self.max_chars] if len(text) > self.max_chars else text

            try:
                response = httpx.post(
                    url,
                    json={"model": self.model_name, "prompt": truncated_text},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
            except httpx.HTTPStatusError as e:
                # Show detailed error information
                error_detail = ""
                try:
                    error_data = e.response.json()
                    error_detail = f" - {error_data.get('error', 'Unknown error')}"
                except Exception:
                    error_detail = f" - Response: {e.response.text[:200]}"

                raise RuntimeError(
                    f"Ollama embedding failed for document {idx + 1}/{len(texts)}: "
                    f"HTTP {e.response.status_code}{error_detail}\n"
                    f"Model: {self.model_name}, Endpoint: {url}\n"
                    f"Text length: {len(text)} chars (truncated to {len(truncated_text)})\n"
                    f"Text preview: {truncated_text[:100]}..."
                ) from e

        return embeddings


def create_embedding_backend(config: Config) -> EmbeddingBackend:
    """Create an embedding backend from configuration.

    The backend is determined by the embedding.backend config value.
    If not specified, it's inferred from the model name:
    - Models starting with "sentence-transformers/" use sentence-transformers
    - Other models use Ollama (default)

    Args:
        config: Application configuration.

    Returns:
        An EmbeddingBackend instance.
    """
    model_name = config.embedding.model
    backend_type = config.embedding.backend

    # Convert string backend to enum if needed
    if isinstance(backend_type, str):
        if backend_type.lower() in ("ollama", "ollama_embedding"):
            backend_type = EmbeddingBackendType.OLLAMA
        elif backend_type.lower() in (
            "sentence-transformers",
            "sentence_transformers",
            "huggingface",
        ):
            backend_type = EmbeddingBackendType.SENTENCE_TRANSFORMERS
        else:
            raise ValueError(f"Unknown embedding backend: {backend_type}")

    # Auto-detect backend if not specified
    if backend_type is None:
        if model_name.startswith("sentence-transformers/"):
            # Explicit sentence-transformers prefix
            backend_type = EmbeddingBackendType.SENTENCE_TRANSFORMERS
        else:
            # Default to Ollama for all other models (no prefix or simple names)
            # This includes: nomic-embed-text, embeddinggemma, mxbai-embed-large, etc.
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
