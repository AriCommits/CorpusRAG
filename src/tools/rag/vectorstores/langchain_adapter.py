"""LangChain VectorStore adapter for pluggable backends."""

from typing import Any


class LangChainVectorStoreAdapter:
    """Adapter that wraps any LangChain VectorStore for use with CorpusRAG strategies.

    Enables using LangChain-compatible vectorstore backends (Qdrant, Pinecone, Weaviate, FAISS, etc.)
    without modifying strategy code.

    Example:
        from langchain_qdrant import QdrantVectorStore
        qdrant_vs = QdrantVectorStore.from_existing(...)
        adapter = LangChainVectorStoreAdapter(qdrant_vs)
        strategy = HybridStrategy(vectorstore=adapter, ...)
    """

    def __init__(self, vectorstore: Any):
        """Initialize LangChain vectorstore adapter.

        Args:
            vectorstore: Any LangChain VectorStore instance
        """
        self.vs = vectorstore

    def add_documents(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadata: list[dict],
        ids: list[str],
    ) -> None:
        """Add documents (not fully supported in LangChain interface).

        Args:
            collection: Collection name (metadata namespace)
            documents: List of document texts
            embeddings: List of embedding vectors
            metadata: List of metadata dicts
            ids: List of document IDs

        Raises:
            NotImplementedError: LangChain VectorStore doesn't support bulk add with embeddings
        """
        raise NotImplementedError(
            "LangChainVectorStoreAdapter requires pre-populated vectorstore. "
            "Use the vectorstore's native methods to add documents."
        )

    def similarity_search(
        self,
        collection: str,
        query_embedding: list[float],
        k: int,
        where: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Search for similar documents using LangChain interface.

        Args:
            collection: Collection name (ignored, LangChain doesn't support namespaces)
            query_embedding: Query embedding vector
            k: Number of results
            where: Metadata filter (passed as filter to LangChain)

        Returns:
            List of result dicts with 'id', 'metadata', 'distance'
        """
        # Use LangChain's similarity_search_by_vector
        docs = self.vs.similarity_search_by_vector(
            embedding=query_embedding,
            k=k,
            filter=where,
        )

        results = []
        for doc in docs:
            results.append(
                {
                    "id": doc.metadata.get("id", ""),
                    "metadata": doc.metadata or {},
                    "distance": 0.0,  # LangChain doesn't return distances directly
                }
            )
        return results

    def delete_by_metadata(self, collection: str, where: dict) -> None:
        """Delete documents matching metadata filter.

        Args:
            collection: Collection name
            where: Metadata filter

        Raises:
            NotImplementedError: LangChain VectorStore doesn't support metadata-based deletion
        """
        raise NotImplementedError(
            "LangChainVectorStoreAdapter doesn't support metadata-based deletion. "
            "Use the vectorstore's native delete methods."
        )

    def collection_exists(self, name: str) -> bool:
        """Check if collection exists (always True for LangChain).

        Args:
            name: Collection name

        Returns:
            True (LangChain doesn't have explicit collection management)
        """
        return True

    def create_collection(self, name: str) -> None:
        """Create a new collection (no-op for LangChain).

        Args:
            name: Collection name
        """
        pass

    def list_collections(self) -> list[str]:
        """List all collections (returns empty for LangChain).

        Returns:
            Empty list (LangChain doesn't expose collection listing)
        """
        return []

    def count_documents(self, collection: str) -> int:
        """Count documents in collection.

        Args:
            collection: Collection name

        Returns:
            Document count (returns 0 - LangChain doesn't provide this)
        """
        return 0

    def get_metadata_by_filter(self, collection: str, where: dict, limit: int) -> list[dict]:
        """Get metadata for documents matching filter.

        Args:
            collection: Collection name
            where: Metadata filter
            limit: Maximum results

        Returns:
            List of metadata dicts

        Raises:
            NotImplementedError: LangChain doesn't support metadata-only queries
        """
        raise NotImplementedError(
            "LangChainVectorStoreAdapter doesn't support metadata-only queries. "
            "Use similarity_search with a dummy embedding instead."
        )

    def query(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> dict:
        """Query collection (raw response format for compatibility).

        Args:
            collection: Collection name
            query_embedding: Query embedding
            n_results: Number of results
            where: Metadata filter

        Returns:
            Dict with 'ids', 'metadatas', 'distances' (ChromaDB-compatible format)
        """
        results = self.similarity_search(collection, query_embedding, n_results, where)

        ids = [[r["id"] for r in results]]
        metadatas = [[r["metadata"] for r in results]]
        distances = [[r["distance"] for r in results]]

        return {
            "ids": ids,
            "metadatas": metadatas,
            "distances": distances,
        }
