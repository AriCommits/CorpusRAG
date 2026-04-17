"""RAG retrieval logic."""

from dataclasses import dataclass
from typing import Any

from db import DatabaseBackend

from .config import RAGConfig
from .embeddings import EmbeddingClient


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved document chunk."""

    id: str
    text: str
    metadata: dict[str, Any]
    semantic_rank: int | None = None
    bm25_rank: int | None = None
    score: float = 0.0


class RAGRetriever:
    """Retrieve relevant documents for RAG queries."""

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        """Initialize RAG retriever.

        Args:
            config: RAG configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        self.embedder = EmbeddingClient(config)

    def semantic_search(
        self, query: str, collection: str, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        """Perform semantic search using embeddings.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of results (uses config default if None)

        Returns:
            List of retrieved chunks
        """
        if top_k is None:
            top_k = self.config.retrieval.top_k_semantic

        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Check if collection exists
        if not self.db.collection_exists(full_collection):
            return []

        query_embedding = self.embedder.embed_query(query)
        results = self.db.query(
            full_collection,
            query_embedding=query_embedding,
            n_results=top_k,
        )

        # Convert to RetrievedChunk objects
        chunks = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids, 1):
            distance = distances[i - 1] if i - 1 < len(distances) else 0.0
            chunks.append(
                RetrievedChunk(
                    id=chunk_id,
                    text=documents[i - 1] if i - 1 < len(documents) else "",
                    metadata=metadatas[i - 1] if i - 1 < len(metadatas) else {},
                    semantic_rank=i,
                    score=1.0 / (1.0 + distance),
                )
            )

        return chunks


    def retrieve(
        self, query: str, collection: str, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        """Main retrieval method using semantic search.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of results (uses config default if None)

        Returns:
            List of retrieved chunks
        """
        return self.semantic_search(query, collection, top_k)
