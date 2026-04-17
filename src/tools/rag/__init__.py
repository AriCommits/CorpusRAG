"""RAG (Retrieval-Augmented Generation) tool."""

# Disable Hugging Face and Transformers loading output globally
try:
    import transformers
    from huggingface_hub.utils import disable_progress_bars

    disable_progress_bars()
    transformers.logging.set_verbosity_error()
except ImportError:
    pass

from .agent import RAGAgent
from .config import RAGConfig
from .ingest import IngestResult, RAGIngester
from .retriever import RAGRetriever, RetrievedDocument

__all__ = [
    "IngestResult",
    "RAGAgent",
    "RAGConfig",
    "RAGIngester",
    "RAGRetriever",
    "RetrievedDocument",
]
