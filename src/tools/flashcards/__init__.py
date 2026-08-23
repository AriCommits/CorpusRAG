"""Flashcard tool for CorpusRAG."""

from .config import FlashcardConfig
from .generator import FlashcardGenerator

# Kept True for MCP callers that still check the old tiktoken gate.
GENERATORS_AVAILABLE = True

__all__ = ["FlashcardConfig", "FlashcardGenerator", "GENERATORS_AVAILABLE"]
