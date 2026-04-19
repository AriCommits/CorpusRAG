"""Base protocol for vectorstore operations."""

from typing import Any, Protocol


class VectorStoreAdapter(Protocol):
    """Protocol for vectorstore operations needed by RAG strategies.

    Any class implementing this protocol can be used as a vectorstore backend.
    """

    def add_documents(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadata: list[dict],
        ids: list[str],
    ) -> None:
        """Add documents to a collection.

        Args:
            collection: Collection name
            documents: List of document texts
            embeddings: List of embedding vectors
            metadata: List of metadata dicts
            ids: List of document IDs
        """
        ...

    def similarity_search(
        self,
        collection: str,
        query_embedding: list[float],
        k: int,
        where: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Search for similar documents.

        Args:
            collection: Collection name
            query_embedding: Query embedding vector
            k: Number of results
            where: Metadata filter

        Returns:
            List of result dicts with 'id', 'text', 'metadata', 'distance'
        """
        ...

    def delete_by_metadata(self, collection: str, where: dict) -> None:
        """Delete documents matching metadata filter.

        Args:
            collection: Collection name
            where: Metadata filter
        """
        ...

    def collection_exists(self, name: str) -> bool:
        """Check if collection exists.

        Args:
            name: Collection name

        Returns:
            True if collection exists
        """
        ...

    def create_collection(self, name: str) -> None:
        """Create a new collection.

        Args:
            name: Collection name
        """
        ...

    def list_collections(self) -> list[str]:
        """List all collections.

        Returns:
            List of collection names
        """
        ...

    def count_documents(self, collection: str) -> int:
        """Count documents in collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents
        """
        ...

    def get_metadata_by_filter(self, collection: str, where: dict, limit: int) -> list[dict]:
        """Get metadata for documents matching filter.

        Args:
            collection: Collection name
            where: Metadata filter
            limit: Maximum results

        Returns:
            List of metadata dicts
        """
        ...

    def query(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> dict:
        """Query collection (raw response format).

        Args:
            collection: Collection name
            query_embedding: Query embedding
            n_results: Number of results
            where: Metadata filter

        Returns:
            Raw query results dict with 'ids', 'metadatas', 'distances'
        """
        ...
