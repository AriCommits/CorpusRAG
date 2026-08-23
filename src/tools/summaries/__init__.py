"""Summary tool for CorpusRAG."""

from .config import SummaryConfig
from .generator import SummaryGenerator

# Kept True for MCP callers that still check the old tiktoken gate.
GENERATORS_AVAILABLE = True

__all__ = ["SummaryConfig", "SummaryGenerator", "GENERATORS_AVAILABLE"]
