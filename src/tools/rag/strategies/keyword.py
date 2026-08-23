"""Keyword-only RAG retrieval using BM25."""

from .staged import StagedStrategy


class KeywordStrategy(StagedStrategy):
    """BM25 keyword search without embeddings."""

    name = "keyword"
    _use_vector = False
    _use_keyword = True
    _use_rerank = False
