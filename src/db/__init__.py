"""Database abstraction layer for CorpusRAG."""

from .base import DatabaseBackend
from .chroma import ChromaDBBackend
from .models import Collection, Document

__all__ = ["ChromaDBBackend", "Collection", "DatabaseBackend", "Document"]
