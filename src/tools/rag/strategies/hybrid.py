"""Hybrid RAG retrieval strategy combining vector and keyword search."""

from typing import Any

import transformers
from huggingface_hub.utils import disable_progress_bars

disable_progress_bars()
transformers.logging.set_verbosity_error()

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from ..config import RAGConfig
from .base import RetrievedDocument

# Allowed metadata operators for security
ALLOWED_METADATA_OPS = {"$contains", "$eq", "$ne", "$in", "$or", "$and"}


class HybridStrategy:
    """Hybrid retrieval: vector search + BM25 keyword search + RRF fusion + reranking.

    This strategy combines vector similarity search with BM25 keyword matching,
    fuses the results using Reciprocal Rank Fusion, then reranks with a cross-encoder.
    """

    name = "hybrid"

    def __init__(self, vectorstore: Any, embedder: Any, parent_store: Any, config: RAGConfig):
        """Initialize hybrid strategy.

        Args:
            vectorstore: Vector store backend (ChromaDB or LangChain adapter)
            embedder: Embedding client for query encoding
            parent_store: Parent document store for retrieving full documents
            config: RAG configuration
        """
        self.vectorstore = vectorstore
        self.embedder = embedder
        self.parent_store = parent_store
        self.config = config

        # BM25 components (lazy initialized per collection)
        self.bm25_index = None
        self.bm25_docs = []

        # Reranker (lazy initialized)
        self.reranker = None
        self.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve documents using hybrid search with reranking.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of documents to retrieve
            where: Optional metadata filter

        Returns:
            List of retrieved documents ranked by cross-encoder score
        """
        # 1. Vector Search (over-fetch)
        vector_docs = self._vector_search(query, collection, top_k * 2, where)

        # 2. Keyword Search (over-fetch)
        keyword_docs = self._keyword_search(query, collection, top_k * 2, where)

        # 3. Hybrid fusion using Reciprocal Rank Fusion (RRF)
        fused_docs = self._rrf_fuse(vector_docs, keyword_docs, top_k * 3)

        if not fused_docs:
            return []

        # 4. Cross-encoder Reranking
        return self._rerank(query, fused_docs, top_k)

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

    def _init_reranker(self) -> None:
        """Initialize cross-encoder reranker."""
        if self.reranker is None:
            self.reranker = CrossEncoder(self.reranker_model)

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

    def _vector_search(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Search child documents in vector store.

        Args:
            query: Query string
            collection: Collection name
            top_k: Number of results to return
            where: Metadata filter

        Returns:
            List of retrieved documents
        """
        full_collection = f"{self.config.collection_prefix}_{collection}"
        if not self.vectorstore.collection_exists(full_collection):
            return []

        query_embedding = self.embedder.embed_query(query)

        # Over-fetch for duplicate parents
        n_results = top_k * 5
        results = self.vectorstore.query(
            full_collection,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        parent_ids_seen = set()
        retrieved_docs = []
        rank = 1

        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, child_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            parent_id = metadata.get("parent_id")

            if not parent_id or parent_id in parent_ids_seen:
                continue

            parent_ids_seen.add(parent_id)

            try:
                parent_doc = self.parent_store.mget([parent_id])
                if parent_doc and parent_doc[0]:
                    doc = parent_doc[0]
                    distance = distances[i] if i < len(distances) else 0.0
                    retrieved_docs.append(
                        RetrievedDocument(
                            id=parent_id,
                            text=doc.page_content,
                            metadata=doc.metadata or {},
                            rank=rank,
                            score=1.0 / (1.0 + distance),
                        )
                    )
                    rank += 1
                    if len(retrieved_docs) >= top_k:
                        break
            except Exception as e:
                print(f"Error retrieving parent document {parent_id}: {e}")

        return retrieved_docs

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

    def _rrf_fuse(
        self,
        vector_docs: list[RetrievedDocument],
        keyword_docs: list[RetrievedDocument],
        top_k: int,
    ) -> list[RetrievedDocument]:
        """Fuse vector and keyword results using Reciprocal Rank Fusion (RRF).

        Args:
            vector_docs: Documents from vector search
            keyword_docs: Documents from keyword search
            top_k: Number of fused results to return

        Returns:
            List of fused documents
        """
        if not vector_docs:
            return keyword_docs[:top_k]
        if not keyword_docs:
            return vector_docs[:top_k]

        rrf_k = self.config.retrieval.rrf_k
        scores = {}  # doc_id -> rrf_score
        docs_by_id = {}

        for doc in vector_docs:
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (rrf_k + doc.rank)
            docs_by_id[doc.id] = doc

        for doc in keyword_docs:
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (rrf_k + doc.rank)
            if doc.id not in docs_by_id:
                docs_by_id[doc.id] = doc

        sorted_ids = sorted(scores.keys(), key=lambda id: scores[id], reverse=True)

        fused_docs = []
        for i, doc_id in enumerate(sorted_ids[:top_k]):
            original_doc = docs_by_id[doc_id]
            fused_docs.append(
                RetrievedDocument(
                    id=doc_id,
                    text=original_doc.text,
                    metadata=original_doc.metadata,
                    rank=i + 1,
                    score=scores[doc_id],
                )
            )

        return fused_docs

    def _rerank(
        self, query: str, docs: list[RetrievedDocument], top_k: int
    ) -> list[RetrievedDocument]:
        """Rerank documents using cross-encoder.

        Args:
            query: Query string
            docs: Documents to rerank
            top_k: Number of results to return

        Returns:
            Reranked documents
        """
        self._init_reranker()

        if not self.reranker or not docs:
            return docs[:top_k]

        # Prepare pairs for cross-encoder
        pairs = [[query, doc.text] for doc in docs]
        cross_scores = self.reranker.predict(pairs)

        # Pair scores with documents and sort
        scored_docs = []
        for i, doc in enumerate(docs):
            scored_docs.append((cross_scores[i], doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # Return top-k reranked documents
        final_docs = []
        for i, (score, doc) in enumerate(scored_docs[:top_k]):
            final_docs.append(
                RetrievedDocument(
                    id=doc.id,
                    text=doc.text,
                    metadata=doc.metadata,
                    rank=i + 1,
                    score=float(score),
                )
            )

        return final_docs
