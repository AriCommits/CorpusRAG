"""Hybrid RAG retrieval: vector + BM25 + RRF + rerank."""

from .staged import StagedStrategy


class HybridStrategy(StagedStrategy):
    """Vector search + BM25 + Reciprocal Rank Fusion + cross-encoder rerank."""

    name = "hybrid"
    _use_vector = True
    _use_keyword = True
    _use_rerank = True
