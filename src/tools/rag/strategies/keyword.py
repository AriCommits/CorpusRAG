"""Keyword-only RAG retrieval strategy using BM25."""

from typing import Any

from rank_bm25 import BM25Okapi

from ..config import RAGConfig
from .base import RetrievedDocument

# Allowed metadata operators for security
ALLOWED_METADATA_OPS = {"$contains", "$eq", "$ne", "$in", "$or", "$and"}


class KeywordStrategy:
    """BM25 keyword search without embeddings.

    Useful for exact-match queries, code search, or when embedding models are unavailable.
    No embedding cost, fastest strategy, but less semantic understanding.
    """

    name = "keyword"

    def __init__(self, vectorstore: Any, embedder: Any, parent_store: Any, config: RAGConfig):
        """Initialize keyword strategy.

        Args:
            vectorstore: Vector store backend (not used)
            embedder: Embedding client (not used)
            parent_store: Parent document store
            config: RAG configuration
        """
        self.parent_store = parent_store
        self.config = config

        # BM25 components
        self.bm25_index = None
        self.bm25_docs = []

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve documents using BM25 keyword search.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of documents to retrieve
            where: Optional metadata filter

        Returns:
            List of retrieved documents ranked by BM25 score
        """
        return self._keyword_search(query, collection, top_k, where)

    def initialize(self, collection: str) -> None:
        """Initialize BM25 index for the collection.

        Args:
            collection: Collection name
        """
        self._init_bm25(collection)

    def _init_bm25(self, collection: str) -> None:
        """Initialize BM25 index for the specified collection.

        Args:
            collection: Collection name
        """
        # Load all documents for the collection
        all_docs = self.parent_store.mget_all()
        # Filter docs that belong to this collection
        collection_docs = [
            (doc_id, doc)
            for doc_id, doc in all_docs
            if doc.metadata.get("collection_name") == collection
            or not doc.metadata.get("collection_name")
        ]

        if not collection_docs:
            return

        self.bm25_docs = collection_docs
        tokenized_corpus = [doc.page_content.lower().split() for _, doc in collection_docs]
        self.bm25_index = BM25Okapi(tokenized_corpus)

    def _apply_metadata_filter(self, doc_metadata: dict, where: dict) -> bool:
        """Apply metadata filter with operator whitelisting.

        Args:
            doc_metadata: Document metadata dict
            where: Filter conditions dict

        Returns:
            True if document matches filter, False otherwise

        Raises:
            ValueError: If unsupported metadata operator is used
        """
        for key, value in where.items():
            if key.startswith("$") and key not in ALLOWED_METADATA_OPS:
                raise ValueError(f"Unsupported metadata operator: {key}")

            # Handle tag-related filters
            for tag_field in ("tags", "tag_prefixes", "tag_leaves"):
                if key == tag_field:
                    tag_condition = value
                    doc_values = doc_metadata.get(tag_field, [])
                    if isinstance(doc_values, str):
                        doc_values = [doc_values]
                    if "$contains" in tag_condition:
                        if tag_condition["$contains"] not in doc_values:
                            return False
                    elif "$or" in tag_condition:
                        match = False
                        for cond in tag_condition["$or"]:
                            val_to_find = cond.get(tag_field, {}).get("$contains")
                            if val_to_find in doc_values:
                                match = True
                                break
                        if not match:
                            return False

        return True

    def _keyword_search(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Search documents using BM25.

        Args:
            query: Query string
            collection: Collection name
            top_k: Number of results to return
            where: Metadata filter

        Returns:
            List of retrieved documents
        """
        if self.bm25_index is None:
            self._init_bm25(collection)

        if not self.bm25_index:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)

        # Rank documents by BM25 score
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        retrieved_docs = []
        rank = 1

        for i in ranked_indices:
            if scores[i] <= 0:
                break

            doc_id, doc = self.bm25_docs[i]

            # Manual metadata filtering for BM25
            if where:
                if not self._apply_metadata_filter(doc.metadata or {}, where):
                    continue

            retrieved_docs.append(
                RetrievedDocument(
                    id=doc_id,
                    text=doc.page_content,
                    metadata=doc.metadata or {},
                    rank=rank,
                    score=float(scores[i]),
                )
            )
            rank += 1
            if len(retrieved_docs) >= top_k:
                break

        return retrieved_docs
