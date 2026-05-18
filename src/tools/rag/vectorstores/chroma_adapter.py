"""ChromaDB adapter implementing VectorStoreAdapter protocol."""

from typing import Any

from db import ChromaDBBackend


class ChromaVectorStore:
    """ChromaDB adapter implementing VectorStoreAdapter protocol.

    Wraps the existing ChromaDBBackend to conform to the VectorStoreAdapter interface.
    """

    def __init__(self, db: ChromaDBBackend):
        """Initialize ChromaDB adapter.

        Args:
            db: ChromaDBBackend instance
        """
        self.db = db

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
        self.db.add_documents(
            collection=collection,
            documents=documents,
            embeddings=embeddings,
            metadata=metadata,
            ids=ids,
        )

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
            List of result dicts
        """
        results = self.query(collection, query_embedding, k, where)
        # Normalize ChromaDB response format
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        normalized = []
        for i, doc_id in enumerate(ids):
            normalized.append(
                {
                    "id": doc_id,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else 0.0,
                }
            )
        return normalized

    def delete_by_metadata(self, collection: str, where: dict) -> None:
        """Delete documents matching metadata filter.

        Args:
            collection: Collection name
            where: Metadata filter
        """
        self.db.delete_by_metadata(collection, where)

    def collection_exists(self, name: str) -> bool:
        """Check if collection exists.

        Args:
            name: Collection name

        Returns:
            True if collection exists
        """
        return self.db.collection_exists(name)

    def create_collection(self, name: str) -> None:
        """Create a new collection.

        Args:
            name: Collection name
        """
        self.db.create_collection(name)

    def list_collections(self) -> list[str]:
        """List all collections.

        Returns:
            List of collection names
        """
        return self.db.list_collections()

    def count_documents(self, collection: str) -> int:
        """Count documents in collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents
        """
        return self.db.count_documents(collection)

    def get_metadata_by_filter(self, collection: str, where: dict, limit: int) -> list[dict]:
        """Get metadata for documents matching filter.

        Args:
            collection: Collection name
            where: Metadata filter
            limit: Maximum results

        Returns:
            List of metadata dicts
        """
        return self.db.get_metadata_by_filter(collection, where, limit)

    def query(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> dict:
        """Query collection.

        Args:
            collection: Collection name
            query_embedding: Query embedding
            n_results: Number of results
            where: Metadata filter

        Returns:
            Raw query results dict
        """
        return self.db.query(collection, query_embedding, n_results, where)
