"""Integration tests for database abstraction layer."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from config.base import DatabaseConfig
from db import ChromaDBBackend, DatabaseBackend


@pytest.fixture
def temp_db_dir() -> Generator[Path, None, None]:
    """Create temporary database directory."""
    # ignore_cleanup_errors avoids Windows file-lock failures on ChromaDB SQLite
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def db_config(temp_db_dir: Path) -> DatabaseConfig:
    """Create test database config."""
    return DatabaseConfig(
        backend="chromadb",
        mode="persistent",
        persist_directory=temp_db_dir,
    )


@pytest.fixture
def db_backend(db_config: DatabaseConfig) -> ChromaDBBackend:
    """Create test database backend."""
    return ChromaDBBackend(db_config)


class TestChromaDBBackend:
    """Integration tests for ChromaDB backend."""

    def test_create_backend(self, db_config: DatabaseConfig) -> None:
        """Test creating ChromaDB backend."""
        backend = ChromaDBBackend(db_config)
        assert isinstance(backend, DatabaseBackend)
        assert backend.config == db_config

    def test_create_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test creating a collection."""
        db_backend.create_collection("test_collection")
        assert db_backend.collection_exists("test_collection")

    def test_create_duplicate_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test creating duplicate collection raises error."""
        db_backend.create_collection("test_collection")
        with pytest.raises(ValueError, match="already exists"):
            db_backend.create_collection("test_collection")

    def test_create_collection_with_metadata(self, db_backend: ChromaDBBackend) -> None:
        """Test creating collection with metadata."""
        metadata = {"tool": "test", "version": "1.0"}
        db_backend.create_collection("test_collection", metadata=metadata)
        assert db_backend.collection_exists("test_collection")

    def test_get_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test getting an existing collection."""
        db_backend.create_collection("test_collection")
        collection = db_backend.get_collection("test_collection")
        assert collection is not None

    def test_get_nonexistent_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test getting nonexistent collection raises error."""
        with pytest.raises(ValueError, match="does not exist"):
            db_backend.get_collection("nonexistent")

    def test_list_collections_empty(self, db_backend: ChromaDBBackend) -> None:
        """Test listing collections when none exist."""
        collections = db_backend.list_collections()
        assert collections == []

    def test_list_collections(self, db_backend: ChromaDBBackend) -> None:
        """Test listing multiple collections."""
        db_backend.create_collection("collection1")
        db_backend.create_collection("collection2")
        db_backend.create_collection("collection3")

        collections = db_backend.list_collections()
        assert len(collections) == 3
        assert "collection1" in collections
        assert "collection2" in collections
        assert "collection3" in collections

    def test_collection_exists(self, db_backend: ChromaDBBackend) -> None:
        """Test checking collection existence."""
        assert not db_backend.collection_exists("test_collection")
        db_backend.create_collection("test_collection")
        assert db_backend.collection_exists("test_collection")

    def test_add_documents(self, db_backend: ChromaDBBackend) -> None:
        """Test adding documents to collection."""
        db_backend.create_collection("test_collection")

        documents = ["doc1", "doc2", "doc3"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        metadata = [{"id": 1}, {"id": 2}, {"id": 3}]
        ids = ["id1", "id2", "id3"]

        db_backend.add_documents(
            "test_collection",
            documents=documents,
            embeddings=embeddings,
            metadata=metadata,
            ids=ids,
        )

        count = db_backend.count_documents("test_collection")
        assert count == 3

    def test_add_documents_mismatched_lengths(self, db_backend: ChromaDBBackend) -> None:
        """Test adding documents with mismatched lengths raises error."""
        db_backend.create_collection("test_collection")

        with pytest.raises(ValueError, match="same length"):
            db_backend.add_documents(
                "test_collection",
                documents=["doc1", "doc2"],
                embeddings=[[0.1, 0.2, 0.3]],  # Wrong length
                metadata=[{"id": 1}, {"id": 2}],
                ids=["id1", "id2"],
            )

    def test_query_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test querying collection."""
        db_backend.create_collection("test_collection")

        # Add some documents
        documents = ["apple", "banana", "cherry"]
        embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        metadata = [{"fruit": "apple"}, {"fruit": "banana"}, {"fruit": "cherry"}]
        ids = ["1", "2", "3"]

        db_backend.add_documents(
            "test_collection",
            documents=documents,
            embeddings=embeddings,
            metadata=metadata,
            ids=ids,
        )

        # Query with similar embedding to "apple"
        results = db_backend.query(
            "test_collection",
            query_embedding=[1.0, 0.0, 0.0],
            n_results=2,
        )

        assert "ids" in results
        assert "documents" in results
        assert "metadatas" in results
        assert "distances" in results

    def test_query_with_filter(self, db_backend: ChromaDBBackend) -> None:
        """Test querying with metadata filter."""
        db_backend.create_collection("test_collection")

        # Add documents with different metadata
        documents = ["red apple", "green apple", "banana"]
        embeddings = [[1.0, 0.0, 0.0], [1.0, 0.1, 0.0], [0.0, 1.0, 0.0]]
        metadata = [
            {"type": "fruit", "color": "red"},
            {"type": "fruit", "color": "green"},
            {"type": "fruit", "color": "yellow"},
        ]
        ids = ["1", "2", "3"]

        db_backend.add_documents(
            "test_collection",
            documents=documents,
            embeddings=embeddings,
            metadata=metadata,
            ids=ids,
        )

        # Query with filter
        results = db_backend.query(
            "test_collection",
            query_embedding=[1.0, 0.0, 0.0],
            n_results=10,
            where={"color": "red"},
        )

        assert len(results["ids"][0]) == 1

    def test_delete_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test deleting collection."""
        db_backend.create_collection("test_collection")
        assert db_backend.collection_exists("test_collection")

        db_backend.delete_collection("test_collection")
        assert not db_backend.collection_exists("test_collection")

    def test_delete_nonexistent_collection(self, db_backend: ChromaDBBackend) -> None:
        """Test deleting nonexistent collection raises error."""
        with pytest.raises(ValueError, match="does not exist"):
            db_backend.delete_collection("nonexistent")

    def test_count_documents_empty(self, db_backend: ChromaDBBackend) -> None:
        """Test counting documents in empty collection."""
        db_backend.create_collection("test_collection")
        count = db_backend.count_documents("test_collection")
        assert count == 0

    def test_count_documents(self, db_backend: ChromaDBBackend) -> None:
        """Test counting documents."""
        db_backend.create_collection("test_collection")

        documents = ["doc1", "doc2", "doc3"]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        metadata = [{}, {}, {}]
        ids = ["1", "2", "3"]

        db_backend.add_documents(
            "test_collection",
            documents=documents,
            embeddings=embeddings,
            metadata=metadata,
            ids=ids,
        )

        count = db_backend.count_documents("test_collection")
        assert count == 3

    def test_collection_namespacing(self, db_backend: ChromaDBBackend) -> None:
        """Test that different collection namespaces are isolated."""
        # Create collections for different tools
        db_backend.create_collection("flashcards_biology")
        db_backend.create_collection("flashcards_history")
        db_backend.create_collection("rag_notes")

        # Add documents to each
        for collection in ["flashcards_biology", "flashcards_history", "rag_notes"]:
            db_backend.add_documents(
                collection,
                documents=[f"doc from {collection}"],
                embeddings=[[0.1, 0.2]],
                metadata=[{"source": collection}],
                ids=[collection],
            )

        # Verify isolation
        assert db_backend.count_documents("flashcards_biology") == 1
        assert db_backend.count_documents("flashcards_history") == 1
        assert db_backend.count_documents("rag_notes") == 1

        # Query one collection shouldn't affect others
        results = db_backend.query("flashcards_biology", query_embedding=[0.1, 0.2], n_results=10)
        assert len(results["ids"][0]) == 1
        assert "flashcards_biology" in results["documents"][0][0]


class TestDatabaseConfigModes:
    """Test different database configuration modes."""

    def test_persistent_mode(self, temp_db_dir: Path) -> None:
        """Test persistent mode creates local database."""
        config = DatabaseConfig(
            mode="persistent",
            persist_directory=temp_db_dir / "chroma_db",
        )
        backend = ChromaDBBackend(config)
        backend.create_collection("test")

        # Verify data persists by creating new backend instance
        backend2 = ChromaDBBackend(config)
        assert backend2.collection_exists("test")

    def test_invalid_mode(self, temp_db_dir: Path) -> None:
        """Test invalid mode raises error."""
        config = DatabaseConfig(
            mode="invalid",  # type: ignore
            persist_directory=temp_db_dir,
        )
        with pytest.raises(ValueError, match="Unknown database mode"):
            ChromaDBBackend(config)
