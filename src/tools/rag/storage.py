"""Local file-based storage for parent documents (backward compatibility shim)."""

from .pipeline.storage import LocalFileStore

__all__ = ["LocalFileStore"]
