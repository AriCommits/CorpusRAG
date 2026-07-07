"""Orchestrations for CorpusRAG.

Pre-composed workflows that combine multiple tools for common use cases.
"""

__all__ = [
    "LecturePipelineOrchestrator",
]


def __getattr__(name: str):
    """Lazy import for orchestration classes."""
    _imports = {
        "LecturePipelineOrchestrator": ".lecture_pipeline",
    }
    if name in _imports:
        import importlib

        module = importlib.import_module(_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
