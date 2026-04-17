"""RAG retrieval logic using parent-child retrieval architecture."""

from dataclasses import dataclass
from typing import Any

import transformers

# Disable Hugging Face and Transformers loading output using their own APIs
from huggingface_hub.utils import disable_progress_bars

disable_progress_bars()
transformers.logging.set_verbosity_error()

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from db import DatabaseBackend

from .config import RAGConfig
from .embeddings import EmbeddingClient
from .storage import LocalFileStore


@dataclass(frozen=True)
class RetrievedDocument:
    """A retrieved parent document."""

    id: str
    text: str
    metadata: dict[str, Any]
    rank: int
    score: float = 0.0


class RAGRetriever:
    """Retrieve relevant documents for RAG using parent-child architecture."""

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        """Initialize RAG retriever.

        Args:
            config: RAG configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        self.embedder = EmbeddingClient(config)

        # Initialize parent document store
        self.config.parent_store.path.mkdir(parents=True, exist_ok=True)
        self.parent_store = LocalFileStore(str(self.config.parent_store.path))

        # Hybrid search components
        self.bm25_index = None
        self.bm25_docs = []

        # Reranker component (lazy loaded)
        self.reranker = None
        self.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def _init_bm25(self, collection: str):
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
            or not doc.metadata.get(
                "collection_name"
            )  # Default to matching if not tagged
        ]

        if not collection_docs:
            return

        self.bm25_docs = collection_docs
        tokenized_corpus = [
            doc.page_content.lower().split() for _, doc in collection_docs
        ]
        self.bm25_index = BM25Okapi(tokenized_corpus)

    def _init_reranker(self):
        """Initialize cross-encoder reranker."""
        if self.reranker is None:
            self.reranker = CrossEncoder(self.reranker_model)

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve parent documents using hybrid (vector + BM25) search with reranking.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of parent documents to retrieve
            where: Metadata filter dict

        Returns:
            List of retrieved parent documents
        """
        if top_k is None:
            top_k = self.config.retrieval.top_k_final

        # 1. Vector Search (over-fetch)
        vector_docs = self._vector_search(query, collection, top_k * 2, where)

        # 2. Keyword Search (over-fetch)
        keyword_docs = self._keyword_search(query, collection, top_k * 2, where)

        # 3. Hybrid fusion using Reciprocal Rank Fusion (RRF)
        # Fetch more candidates for reranking
        fused_docs = self._fuse_results(vector_docs, keyword_docs, top_k * 3)

        if not fused_docs:
            return []

        # 4. Cross-encoder Reranking
        return self._rerank(query, fused_docs, top_k)

    def _vector_search(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Search child documents in vector store."""
        full_collection = f"{self.config.collection_prefix}_{collection}"
        if not self.db.collection_exists(full_collection):
            return []

        query_embedding = self.embedder.embed_query(query)

        # Over-fetch for duplicate parents
        n_results = top_k * 5
        results = self.db.query(
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
        """Search documents using BM25."""
        if self.bm25_index is None:
            self._init_bm25(collection)

        if not self.bm25_index:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)

        # Rank documents by BM25 score
        ranked_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )

        retrieved_docs = []
        rank = 1

        for i in ranked_indices:
            if scores[i] <= 0:
                break

            doc_id, doc = self.bm25_docs[i]

            # Manual metadata filtering for BM25 (since it doesn't support ChromaDB 'where')
            if where:
                if "tags" in where:
                    tag_condition = where["tags"]
                    doc_tags = doc.metadata.get("tags", [])
                    if "$contains" in tag_condition:
                        if tag_condition["$contains"] not in doc_tags:
                            continue
                    elif "$or" in tag_condition:
                        match = False
                        for cond in tag_condition["$or"]:
                            tag_to_find = cond.get("tags", {}).get("$contains")
                            if tag_to_find in doc_tags:
                                match = True
                                break
                        if not match:
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

    def _fuse_results(
        self,
        vector_docs: list[RetrievedDocument],
        keyword_docs: list[RetrievedDocument],
        top_k: int,
    ) -> list[RetrievedDocument]:
        """Fuse vector and keyword results using Reciprocal Rank Fusion (RRF)."""
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
        """Rerank documents using cross-encoder."""
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
