"""Database abstraction layer for CorpusRAG."""

from .base import DatabaseBackend
from .chroma import ChromaDBBackend

__all__ = ["ChromaDBBackend", "DatabaseBackend"]
