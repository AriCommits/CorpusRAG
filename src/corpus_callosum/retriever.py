"""Hybrid retrieval for CorpusCallosum."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .chroma import create_chroma_client
from .config import Config, get_config


@dataclass(slots=True, frozen=True)
class RetrievedChunk:
    id: str
    text: str
    metadata: dict[str, Any]
    semantic_rank: int | None = None
    bm25_rank: int | None = None
    score: float = 0.0


def _normalize_token(token: str) -> str:
    return "".join(ch.lower() for ch in token if ch.isalnum())


def _tokenize(text: str) -> list[str]:
    return [normalized for normalized in (_normalize_token(p) for p in text.split()) if normalized]


class HybridRetriever:
    """Combines semantic and keyword retrieval with RRF."""

    def __init__(
        self,
        *,
        config: Config | None = None,
        chroma_client: Any | None = None,
        embedding_model: SentenceTransformer | None = None,
    ) -> None:
        self.config = config or get_config()
        self.client = chroma_client or create_chroma_client(self.config)
        self._embedding_model = embedding_model

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.config.embedding.model)
        return self._embedding_model

    def semantic_search(self, *, query: str, collection_name: str) -> list[RetrievedChunk]:
        collection = self._get_existing_collection(collection_name)
        if collection is None:
            return []

        if collection.count() == 0:
            return []

        query_embedding = self.embedding_model.encode([query], show_progress_bar=False).tolist()
        top_k = self.config.retrieval.top_k_semantic

        result = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]

        output: list[RetrievedChunk] = []
        for rank, chunk_id in enumerate(ids, start=1):
            output.append(
                RetrievedChunk(
                    id=chunk_id,
                    text=docs[rank - 1],
                    metadata=metadatas[rank - 1] or {},
                    semantic_rank=rank,
                )
            )
        return output

    def bm25_search(self, *, query: str, collection_name: str) -> list[RetrievedChunk]:
        collection = self._get_existing_collection(collection_name)
        if collection is None:
            return []

        result = collection.get(include=["documents", "metadatas"])

        ids = result.get("ids", [])
        docs = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        if not ids:
            return []

        tokenized_docs = [_tokenize(doc) for doc in docs]
        if not any(tokenized_docs):
            return []

        bm25 = BM25Okapi(tokenized_docs)
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)
        ranked_indices = sorted(
            range(len(ids)), key=lambda idx: float(scores[idx]), reverse=True
        )[: self.config.retrieval.top_k_bm25]

        output: list[RetrievedChunk] = []
        for rank, idx in enumerate(ranked_indices, start=1):
            output.append(
                RetrievedChunk(
                    id=ids[idx],
                    text=docs[idx],
                    metadata=metadatas[idx] or {},
                    bm25_rank=rank,
                )
            )
        return output

    def retrieve(self, *, query: str, collection_name: str) -> list[RetrievedChunk]:
        semantic = self.semantic_search(query=query, collection_name=collection_name)
        bm25 = self.bm25_search(query=query, collection_name=collection_name)

        merged: dict[str, RetrievedChunk] = {}
        rrf_scores: dict[str, float] = {}
        k = float(self.config.retrieval.rrf_k)

        for chunk in semantic:
            merged[chunk.id] = chunk
            rrf_scores[chunk.id] = 1.0 / (k + float(chunk.semantic_rank or 0))

        for chunk in bm25:
            existing = merged.get(chunk.id)
            if existing is None:
                merged[chunk.id] = chunk
            else:
                merged[chunk.id] = RetrievedChunk(
                    id=existing.id,
                    text=existing.text,
                    metadata=existing.metadata,
                    semantic_rank=existing.semantic_rank,
                    bm25_rank=chunk.bm25_rank,
                )
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + 1.0 / (
                k + float(chunk.bm25_rank or 0)
            )

        ranked = sorted(merged.values(), key=lambda chunk: rrf_scores.get(chunk.id, 0.0), reverse=True)
        output: list[RetrievedChunk] = []
        for chunk in ranked[: self.config.retrieval.top_k_final]:
            output.append(
                RetrievedChunk(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    semantic_rank=chunk.semantic_rank,
                    bm25_rank=chunk.bm25_rank,
                    score=rrf_scores.get(chunk.id, 0.0),
                )
            )
        return output

    def list_collections(self) -> list[str]:
        return sorted(collection.name for collection in self.client.list_collections())

    def collection_documents(self, collection_name: str) -> list[RetrievedChunk]:
        collection = self._get_existing_collection(collection_name)
        if collection is None:
            return []

        result = collection.get(include=["documents", "metadatas"])
        ids = result.get("ids", [])
        docs = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        return [
            RetrievedChunk(
                id=ids[idx],
                text=docs[idx],
                metadata=metadatas[idx] or {},
            )
            for idx in range(len(ids))
        ]

    def _get_existing_collection(self, collection_name: str) -> Any | None:
        try:
            return self.client.get_collection(name=collection_name)
        except Exception:
            return None
