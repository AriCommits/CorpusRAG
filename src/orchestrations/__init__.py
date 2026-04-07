"""
Orchestrations for Corpus Callosum.

Pre-composed workflows that combine multiple tools for common use cases.
"""

from corpus_callosum.orchestrations.study_session import StudySessionOrchestrator
from corpus_callosum.orchestrations.lecture_pipeline import LecturePipelineOrchestrator
from corpus_callosum.orchestrations.knowledge_base import KnowledgeBaseOrchestrator

__all__ = [
    "StudySessionOrchestrator",
    "LecturePipelineOrchestrator",
    "KnowledgeBaseOrchestrator",
]
