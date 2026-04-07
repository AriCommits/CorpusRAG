"""RAG retrieval logic."""

from dataclasses import dataclass
from typing import Any, Optional

from corpus_callosum.db import DatabaseBackend

from .config import RAGConfig


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved document chunk."""
    
    id: str
    text: str
    metadata: dict[str, Any]
    semantic_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
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

    def semantic_search(
        self, query: str, collection: str, top_k: Optional[int] = None
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
            top_k = self.config.retrieval.top_k

        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Check if collection exists
        if not self.db.collection_exists(full_collection):
            return []

        # Query the database
        results = self.db.query(
            collection_name=full_collection,
            query_text=query,
            n_results=top_k,
        )

        # Convert to RetrievedChunk objects
        chunks = []
        for i, result in enumerate(results, 1):
            chunks.append(
                RetrievedChunk(
                    id=result.id,
                    text=result.content,
                    metadata=result.metadata,
                    semantic_rank=i,
                    score=result.score,
                )
            )

        return chunks

    def bm25_search(
        self, query: str, collection: str, top_k: Optional[int] = None
    ) -> list[RetrievedChunk]:
        """Perform BM25 keyword search.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of results (uses config default if None)

        Returns:
            List of retrieved chunks
        """
        # For now, return empty list (BM25 implementation pending)
        # Full implementation would:
        # 1. Tokenize the query
        # 2. Retrieve all documents from collection
        # 3. Build BM25 index
        # 4. Rank documents and return top-k
        
        return []

    def hybrid_search(
        self, query: str, collection: str, top_k: Optional[int] = None
    ) -> list[RetrievedChunk]:
        """Perform hybrid search combining semantic and BM25.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of results (uses config default if None)

        Returns:
            List of retrieved chunks with combined ranking
        """
        # For now, just use semantic search
        # Full implementation would:
        # 1. Run both semantic and BM25 search
        # 2. Combine results using Reciprocal Rank Fusion (RRF)
        # 3. Return top-k results
        
        return self.semantic_search(query, collection, top_k)

    def retrieve(
        self, query: str, collection: str, top_k: Optional[int] = None
    ) -> list[RetrievedChunk]:
        """Main retrieval method using configured strategy.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of results (uses config default if None)

        Returns:
            List of retrieved chunks
        """
        return self.hybrid_search(query, collection, top_k)
