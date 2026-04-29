"""Orchestrations for CorpusRAG.

Pre-composed workflows that combine multiple tools for common use cases.
"""

__all__ = [
    "KnowledgeBaseOrchestrator",
    "LecturePipelineOrchestrator",
    "StudySessionOrchestrator",
]


def __getattr__(name: str):
    """Lazy import for orchestration classes."""
    _imports = {
        "KnowledgeBaseOrchestrator": ".knowledge_base",
        "LecturePipelineOrchestrator": ".lecture_pipeline",
        "StudySessionOrchestrator": ".study_session",
    }
    if name in _imports:
        import importlib
        module = importlib.import_module(_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
