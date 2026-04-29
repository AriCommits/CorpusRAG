"""RAG (Retrieval-Augmented Generation) tool."""

__all__ = [
    "IngestResult",
    "RAGAgent",
    "RAGConfig",
    "RAGIngester",
    "RAGRetriever",
    "RAGSyncer",
    "RetrievedDocument",
    "SyncResult",
]

_hf_silenced = False


def silence_hf_logging():
    """Silence Hugging Face logging. Call before importing transformers."""
    global _hf_silenced
    if _hf_silenced:
        return
    _hf_silenced = True
    try:
        import transformers
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars()
        transformers.logging.set_verbosity_error()
    except ImportError:
        pass


def __getattr__(name: str):
    """Lazy import for heavy RAG classes."""
    _imports = {
        "RAGConfig": ".config",
        "RAGAgent": ".agent",
        "RAGIngester": ".ingest",
        "IngestResult": ".ingest",
        "RAGRetriever": ".retriever",
        "RetrievedDocument": ".retriever",
        "RAGSyncer": ".sync",
        "SyncResult": ".sync",
    }
    if name in _imports:
        import importlib
        module = importlib.import_module(_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
