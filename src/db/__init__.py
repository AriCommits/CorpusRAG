"""Database abstraction layer for CorpusRAG."""

from .base import DatabaseBackend

__all__ = ["ChromaDBBackend", "DatabaseBackend"]


def __getattr__(name: str):
    """Lazy import for the heavy Chroma backend.

    ``ChromaDBBackend`` pulls in ``chromadb`` (and its transitive
    dependencies), so it is imported only on first access rather than at
    package import time.
    """
    _imports = {
        "ChromaDBBackend": ".chroma",
    }
    if name in _imports:
        import importlib

        module = importlib.import_module(_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
