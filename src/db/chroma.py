"""ChromaDB backend implementation."""

from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import ClientAPI

from ..config.base import DatabaseConfig

from .base import DatabaseBackend


class ChromaDBBackend(DatabaseBackend):
    """ChromaDB implementation of database backend."""

    def __init__(self, config: DatabaseConfig):
        """Initialize ChromaDB backend.

        Args:
            config: Database configuration
        """
        self.config = config

        if config.mode == "persistent":
            self.client: ClientAPI = chromadb.PersistentClient(
                path=str(config.persist_directory)
            )
        elif config.mode == "http":
            self.client = chromadb.HttpClient(
                host=config.host,
                port=config.port,
            )
        else:
            raise ValueError(f"Unknown database mode: {config.mode}")

    def create_collection(
        self, name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a new collection.

        Args:
            name: Collection name
            metadata: Optional collection metadata

        Raises:
            ValueError: If collection already exists
        """
        try:
            self.client.create_collection(name=name, metadata=metadata or {})
        except Exception as e:
            if "already exists" in str(e).lower():
                raise ValueError(f"Collection '{name}' already exists")
            raise

    def get_collection(self, name: str) -> Any:
        """Get existing collection.

        Args:
            name: Collection name

        Returns:
            Collection object

        Raises:
            ValueError: If collection doesn't exist
        """
        try:
            return self.client.get_collection(name=name)
        except Exception as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                raise ValueError(f"Collection '{name}' does not exist")
            raise

    def list_collections(self) -> List[str]:
        """List all collection names.

        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [col.name for col in collections]

    def collection_exists(self, name: str) -> bool:
        """Check if collection exists.

        Args:
            name: Collection name

        Returns:
            True if collection exists, False otherwise
        """
        try:
            self.client.get_collection(name=name)
            return True
        except Exception:
            return False

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
        if not (len(documents) == len(embeddings) == len(metadata) == len(ids)):
            raise ValueError(
                "documents, embeddings, metadata, and ids must have same length"
            )

        col = self.get_collection(collection)
        col.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadata,
            ids=ids,
        )

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
        col = self.get_collection(collection)
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        return results

    def delete_collection(self, name: str) -> None:
        """Delete collection.

        Args:
            name: Collection name

        Raises:
            ValueError: If collection doesn't exist
        """
        try:
            self.client.delete_collection(name=name)
        except Exception as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                raise ValueError(f"Collection '{name}' does not exist")
            raise

    def count_documents(self, collection: str) -> int:
        """Count documents in collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents

        Raises:
            ValueError: If collection doesn't exist
        """
        col = self.get_collection(collection)
        return col.count()
