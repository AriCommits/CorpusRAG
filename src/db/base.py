"""Abstract database backend interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DatabaseBackend(ABC):
    """Abstract database interface for vector stores."""

    @abstractmethod
    def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Create a new collection.

        Args:
            name: Collection name
            metadata: Optional collection metadata

        Raises:
            ValueError: If collection already exists
        """
        pass

    @abstractmethod
    def get_collection(self, name: str) -> Any:
        """Get existing collection.

        Args:
            name: Collection name

        Returns:
            Collection object

        Raises:
            ValueError: If collection doesn't exist
        """
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        """List all collection names.

        Returns:
            List of collection names
        """
        pass

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        """Check if collection exists.

        Args:
            name: Collection name

        Returns:
            True if collection exists, False otherwise
        """
        pass

    @abstractmethod
    def add_documents(
        self,
        collection: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """Add documents to collection.

        Args:
            collection: Collection name
            documents: List of document texts
            embeddings: List of embedding vectors
            metadata: List of metadata dicts
            ids: List of document IDs

        Raises:
            ValueError: If collection doesn't exist or lengths don't match
        """
        pass

    @abstractmethod
    def query(
        self,
        collection: str,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query collection with embedding.

        Args:
            collection: Collection name
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Query results dict with 'ids', 'documents', 'metadatas', 'distances'

        Raises:
            ValueError: If collection doesn't exist
        """
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete collection.

        Args:
            name: Collection name

        Raises:
            ValueError: If collection doesn't exist
        """
        pass

    @abstractmethod
    def count_documents(self, collection: str) -> int:
        """Count documents in collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents

        Raises:
            ValueError: If collection doesn't exist
        """
        pass
