"""VectorStore adapters for pluggable backends."""

from .base import VectorStoreAdapter
from .chroma_adapter import ChromaVectorStore

__all__ = [
    "VectorStoreAdapter",
    "ChromaVectorStore",
]
