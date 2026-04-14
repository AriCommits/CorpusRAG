"""Embedding helpers for RAG ingestion and retrieval."""

from typing import Sequence

import httpx

from .config import RAGConfig


class EmbeddingClient:
    """Generate embeddings using the configured backend."""

    def __init__(self, config: RAGConfig):
        self.config = config

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple texts."""
        if not texts:
            return []

        backend = self.config.embedding.backend
        if backend == "ollama":
            return self._embed_with_ollama(list(texts))
        if backend == "sentence-transformers":
            return self._embed_with_sentence_transformers(list(texts))

        raise ValueError(f"Unsupported embedding backend: {backend}")

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []

    def _embed_with_ollama(self, texts: list[str]) -> list[list[float]]:
        endpoint = self.config.llm.endpoint.rstrip("/")
        timeout = httpx.Timeout(self.config.llm.timeout_seconds)
        response = httpx.post(
            f"{endpoint}/api/embed",
            json={"model": self.config.embedding.model, "input": texts},
            timeout=timeout,
        )

        if response.status_code == 404:
            try:
                error_message = response.json().get("error", "")
            except ValueError:
                error_message = response.text

            # Ollama may return 404 when the model is missing, not only when the route is missing.
            if "model" in error_message.lower() and "not found" in error_message.lower():
                raise ValueError(
                    f"Embedding model '{self.config.embedding.model}' is not available in Ollama. "
                    "Set CC_EMBEDDING_MODEL to an installed embedding model or pull the configured one."
                )

            legacy_response = httpx.post(
                f"{endpoint}/api/embeddings",
                json={"model": self.config.embedding.model, "prompt": texts[0]},
                timeout=timeout,
            )
            if legacy_response.status_code != 404:
                legacy_response.raise_for_status()
                legacy_data = legacy_response.json()
                embedding = legacy_data.get("embedding")
                if not isinstance(embedding, list):
                    raise ValueError(
                        "Legacy Ollama embedding response did not include an embedding"
                    )
                embeddings = [embedding]
                for text in texts[1:]:
                    item_response = httpx.post(
                        f"{endpoint}/api/embeddings",
                        json={"model": self.config.embedding.model, "prompt": text},
                        timeout=timeout,
                    )
                    item_response.raise_for_status()
                    item_data = item_response.json()
                    item_embedding = item_data.get("embedding")
                    if not isinstance(item_embedding, list):
                        raise ValueError(
                            "Legacy Ollama embedding response did not include an embedding"
                        )
                    embeddings.append(item_embedding)
                return embeddings

            openai_response = httpx.post(
                f"{endpoint}/v1/embeddings",
                json={"model": self.config.embedding.model, "input": texts},
                timeout=timeout,
            )
            openai_response.raise_for_status()
            openai_data = openai_response.json()
            data_items = openai_data.get("data", [])
            embeddings = [item.get("embedding") for item in data_items]
            if len(embeddings) != len(texts) or any(not isinstance(item, list) for item in embeddings):
                raise ValueError("OpenAI-compatible Ollama embedding response was invalid")
            return embeddings

        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [])
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ValueError("Ollama embedding response did not match requested text count")
        return embeddings

    def _embed_with_sentence_transformers(self, texts: list[str]) -> list[list[float]]:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for this embedding backend"
            ) from exc

        model = SentenceTransformer(self.config.embedding.model)
        vectors = model.encode(texts)
        return [vector.tolist() for vector in vectors]
