"""Staged RAG retrieval: vector, BM25, RRF, and optional cross-encoder rerank."""

from __future__ import annotations

from typing import Any

from rank_bm25 import BM25Okapi

from ..config import RAGConfig
from .base import RetrievedDocument

ALLOWED_METADATA_OPS = {"$contains", "$eq", "$ne", "$in", "$or", "$and"}


class StagedStrategy:
    """One retrieval implementation parameterized by which stages run."""

    name = "staged"
    _use_vector = True
    _use_keyword = True
    _use_rerank = True

    def __init__(self, vectorstore: Any, embedder: Any, parent_store: Any, config: RAGConfig):
        self.vectorstore = vectorstore
        self.embedder = embedder
        self.parent_store = parent_store
        self.config = config
        self._bm25: dict[str, tuple[Any, list]] = {}
        self.reranker = None

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        vector_k = self.config.retrieval.top_k_semantic or top_k * 2
        keyword_k = self.config.retrieval.top_k_bm25 or top_k * 2

        vector_docs = (
            self._vector_search(query, collection, max(vector_k, top_k * 2), where)
            if self._use_vector
            else []
        )
        keyword_docs = (
            self._keyword_search(query, collection, max(keyword_k, top_k * 2), where)
            if self._use_keyword
            else []
        )

        if self._use_vector and self._use_keyword:
            fused = self._rrf_fuse(vector_docs, keyword_docs, top_k * 3)
        elif self._use_vector:
            fused = vector_docs
        else:
            fused = keyword_docs

        if not fused:
            return []

        if self._use_rerank and self.config.reranking.enabled:
            return self._rerank(query, fused, top_k)
        return fused[:top_k]

    def initialize(self, collection: str) -> None:
        if self._use_keyword:
            self._init_bm25(collection)

    def _init_bm25(self, collection: str) -> None:
        all_docs = self.parent_store.mget_all()
        collection_docs = [
            (doc_id, doc)
            for doc_id, doc in all_docs
            if doc.metadata.get("collection_name") == collection
        ]
        if not collection_docs:
            self._bm25.pop(collection, None)
            return
        tokenized = [doc.page_content.lower().split() for _, doc in collection_docs]
        self._bm25[collection] = (BM25Okapi(tokenized), collection_docs)

    def _init_reranker(self) -> None:
        if self.reranker is None:
            import transformers
            from huggingface_hub.utils import disable_progress_bars
            from sentence_transformers import CrossEncoder

            disable_progress_bars()
            transformers.logging.set_verbosity_error()
            self.reranker = CrossEncoder(self.config.reranking.model)

    def _apply_metadata_filter(self, doc_metadata: dict, where: dict) -> bool:
        for key, value in where.items():
            if key.startswith("$") and key not in ALLOWED_METADATA_OPS:
                raise ValueError(f"Unsupported metadata operator: {key}")

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

        parent_ids_seen: set[str] = set()
        retrieved_docs: list[RetrievedDocument] = []
        rank = 1

        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, _child_id in enumerate(ids):
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
            except Exception:
                continue
        return retrieved_docs

    def _keyword_search(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        if collection not in self._bm25:
            self._init_bm25(collection)
        packed = self._bm25.get(collection)
        if not packed:
            return []
        bm25_index, bm25_docs = packed

        tokenized_query = query.lower().split()
        scores = bm25_index.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        retrieved_docs: list[RetrievedDocument] = []
        rank = 1
        for i in ranked_indices:
            if scores[i] <= 0:
                break
            doc_id, doc = bm25_docs[i]
            if where and not self._apply_metadata_filter(doc.metadata or {}, where):
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
        if not vector_docs:
            return keyword_docs[:top_k]
        if not keyword_docs:
            return vector_docs[:top_k]

        rrf_k = self.config.retrieval.rrf_k
        scores: dict[str, float] = {}
        docs_by_id: dict[str, RetrievedDocument] = {}
        for doc in vector_docs:
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (rrf_k + doc.rank)
            docs_by_id[doc.id] = doc
        for doc in keyword_docs:
            scores[doc.id] = scores.get(doc.id, 0.0) + 1.0 / (rrf_k + doc.rank)
            docs_by_id.setdefault(doc.id, doc)

        fused: list[RetrievedDocument] = []
        for i, doc_id in enumerate(sorted(scores, key=lambda d: scores[d], reverse=True)[:top_k]):
            original = docs_by_id[doc_id]
            fused.append(
                RetrievedDocument(
                    id=doc_id,
                    text=original.text,
                    metadata=original.metadata,
                    rank=i + 1,
                    score=scores[doc_id],
                )
            )
        return fused

    def _rerank(
        self, query: str, docs: list[RetrievedDocument], top_k: int
    ) -> list[RetrievedDocument]:
        self._init_reranker()
        if not self.reranker or not docs:
            return docs[:top_k]
        pairs = [[query, doc.text] for doc in docs]
        cross_scores = self.reranker.predict(pairs)
        scored = sorted(zip(cross_scores, docs, strict=False), key=lambda x: x[0], reverse=True)
        return [
            RetrievedDocument(
                id=doc.id,
                text=doc.text,
                metadata=doc.metadata,
                rank=i + 1,
                score=float(score),
            )
            for i, (score, doc) in enumerate(scored[:top_k])
        ]
