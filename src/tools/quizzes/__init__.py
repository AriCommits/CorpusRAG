"""Quiz generation tool."""

from .config import QuizConfig
from .generator import QuizGenerator

# Kept True for MCP callers that still check the old tiktoken gate.
GENERATORS_AVAILABLE = True

__all__ = ["QuizConfig", "QuizGenerator", "GENERATORS_AVAILABLE"]
