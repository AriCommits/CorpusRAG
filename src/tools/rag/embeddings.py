"""Embedding helpers for RAG ingestion and retrieval (backward compatibility shim)."""

from .pipeline.embeddings import EmbeddingClient

__all__ = ["EmbeddingClient"]
