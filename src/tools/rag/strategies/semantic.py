"""Semantic-only RAG retrieval: vector search + optional rerank."""

from .staged import StagedStrategy


class SemanticStrategy(StagedStrategy):
    """Pure vector similarity search with optional cross-encoder rerank."""

    name = "semantic"
    _use_vector = True
    _use_keyword = False
    _use_rerank = True
