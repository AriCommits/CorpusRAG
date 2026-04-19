"""Semantic-only RAG retrieval strategy using vector search."""

from typing import Any

import transformers
from huggingface_hub.utils import disable_progress_bars

disable_progress_bars()
transformers.logging.set_verbosity_error()

from sentence_transformers import CrossEncoder

from ..config import RAGConfig
from .base import RetrievedDocument


class SemanticStrategy:
    """Pure vector similarity search with optional reranking.

    Faster than hybrid (skips BM25 indexing), good for semantic matching on
    natural language queries where keyword noise is undesirable.
    """

    name = "semantic"

    def __init__(self, vectorstore: Any, embedder: Any, parent_store: Any, config: RAGConfig):
        """Initialize semantic strategy.

        Args:
            vectorstore: Vector store backend
            embedder: Embedding client for query encoding
            parent_store: Parent document store
            config: RAG configuration
        """
        self.vectorstore = vectorstore
        self.embedder = embedder
        self.parent_store = parent_store
        self.config = config

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
        """Retrieve documents using vector search with optional reranking.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of documents to retrieve
            where: Optional metadata filter

        Returns:
            List of retrieved documents
        """
        # Vector search with over-fetch for reranking
        vector_docs = self._vector_search(query, collection, top_k * 3, where)

        if not vector_docs:
            return []

        # Optional reranking
        return self._rerank(query, vector_docs, top_k)

    def initialize(self, collection: str) -> None:
        """Initialize strategy for collection (no-op for semantic).

        Args:
            collection: Collection name
        """
        pass

    def _init_reranker(self) -> None:
        """Initialize cross-encoder reranker."""
        if self.reranker is None:
            self.reranker = CrossEncoder(self.reranker_model)

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

        pairs = [[query, doc.text] for doc in docs]
        cross_scores = self.reranker.predict(pairs)

        scored_docs = []
        for i, doc in enumerate(docs):
            scored_docs.append((cross_scores[i], doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

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
