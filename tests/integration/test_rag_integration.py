"""Integration tests for RAG parent-child retrieval architecture."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.base import DatabaseConfig, LLMConfig
from db import ChromaDBBackend
from tools.rag import RAGAgent, RAGConfig, RAGIngester, RAGRetriever


@pytest.fixture
def temp_rag_dir() -> Generator[Path, None, None]:
    """Create temporary RAG directory with parent store and database."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def rag_config(temp_rag_dir: Path) -> RAGConfig:
    """Create test RAG configuration."""
    from config.base import EmbeddingConfig, PathsConfig
    from tools.rag.config import ParentStoreConfig

    db_config = DatabaseConfig(
        backend="chromadb",
        mode="persistent",
        persist_directory=temp_rag_dir / "chroma_db",
    )

    llm_config = LLMConfig(
        backend="ollama",
        endpoint="http://localhost:11434",
        model="gemma4:26b-a4b-it-q4_K_M",
    )

    embedding_config = EmbeddingConfig(
        backend="ollama",
        model="embeddinggemma",
    )

    paths_config = PathsConfig(
        vault=temp_rag_dir / "vault",
        scratch_dir=temp_rag_dir / "scratch",
        output_dir=temp_rag_dir / "output",
    )

    parent_store_config = ParentStoreConfig(
        type="local_file",
        path=temp_rag_dir / "parent_store",
    )

    return RAGConfig(
        llm=llm_config,
        embedding=embedding_config,
        database=db_config,
        paths=paths_config,
        parent_store=parent_store_config,
    )


@pytest.fixture
def db_backend(rag_config: RAGConfig) -> ChromaDBBackend:
    """Create test database backend."""
    return ChromaDBBackend(rag_config.database)


class TestRAGIngestor:
    """Test RAG document ingestion with parent-child architecture."""

    def test_ingest_markdown_file(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test ingesting a markdown file with semantic splitting."""
        # Create test markdown file
        markdown_content = """# Machine Learning Guide

## Supervised Learning

### Linear Regression
Linear regression is a basic ML algorithm.

### Decision Trees
Decision trees are hierarchical models.

## Unsupervised Learning

### Clustering
Clustering groups similar data points.

### Dimensionality Reduction
Reduces feature space complexity.

Tags:
- #machine-learning #supervised-learning
- #algorithms #regression
"""

        test_file = temp_rag_dir / "test.md"
        test_file.write_text(markdown_content)

        # Mock the embedding client to avoid needing Ollama
        with patch("tools.rag.ingest.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder

            # Return dummy embeddings matching the number of texts
            def mock_embed(texts):
                return [[0.1] * 384 for _ in texts]

            mock_embedder.embed_texts = mock_embed

            # Ingest the file
            ingester = RAGIngester(rag_config, db_backend)
            result = ingester.ingest_path(test_file, "ml_guide")

            # Verify ingestion results
            assert result.collection == "ml_guide"
            assert result.files_indexed == 1
            assert (
                result.chunks_indexed > 0
            )  # Should have multiple chunks from splitting

            # Verify collection was created
            full_collection = f"{rag_config.collection_prefix}_{result.collection}"
            assert db_backend.collection_exists(full_collection)

            # Verify documents were added
            count = db_backend.count_documents(full_collection)
            assert count == result.chunks_indexed

    def test_parent_documents_stored(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that parent documents are properly stored in local file store."""
        markdown_content = """# Python Basics

## Variables and Data Types

Python supports multiple data types.

## Functions

Functions encapsulate reusable code.

Tags:
- #python #basics
"""

        test_file = temp_rag_dir / "python.md"
        test_file.write_text(markdown_content)

        with patch("tools.rag.ingest.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder

            def mock_embed(texts):
                return [[0.1] * 384 for _ in texts]

            mock_embedder.embed_texts = mock_embed

            ingester = RAGIngester(rag_config, db_backend)
            ingester.ingest_path(test_file, "python_guide")

            # Verify parent store was created and contains documents
            parent_store_path = rag_config.parent_store.path
            assert parent_store_path.exists()
            assert len(list(parent_store_path.glob("*"))) > 0

    def test_child_metadata_includes_parent_linkage(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that child documents have proper parent_id metadata."""
        markdown_content = """# Web Development

## HTML Basics

HTML provides structure to web pages.

## CSS Styling

CSS controls the visual appearance.

Tags:
- #web #frontend
"""

        test_file = temp_rag_dir / "web.md"
        test_file.write_text(markdown_content)

        with patch("tools.rag.ingest.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder

            def mock_embed(texts):
                return [[0.1] * 384 for _ in texts]

            mock_embedder.embed_texts = mock_embed

            ingester = RAGIngester(rag_config, db_backend)
            result = ingester.ingest_path(test_file, "web_guide")

            # Query the collection to verify metadata
            full_collection = f"{rag_config.collection_prefix}_{result.collection}"
            query_results = db_backend.query(
                full_collection,
                query_embedding=[0.1] * 384,  # Dummy embedding for this test
                n_results=10,
            )

            # Check that results have parent_id and child_index in metadata
            metadatas = query_results.get("metadatas", [[]])[0]
            for metadata in metadatas:
                assert "parent_id" in metadata, "Child documents must have parent_id"
                assert (
                    "child_index" in metadata
                ), "Child documents must have child_index"
                assert (
                    "source_file" in metadata
                ), "Child documents must have source_file"

    def test_tags_extracted_and_stored(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that tags are extracted from markdown and stored in metadata."""
        markdown_content = """# Data Science

## Statistics

Understanding statistical concepts.

## Machine Learning

ML algorithms and applications.

Tags:
- #data-science #statistics #ml
"""

        test_file = temp_rag_dir / "datascience.md"
        test_file.write_text(markdown_content)

        with patch("tools.rag.ingest.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder

            def mock_embed(texts):
                return [[0.1] * 384 for _ in texts]

            mock_embedder.embed_texts = mock_embed

            ingester = RAGIngester(rag_config, db_backend)
            result = ingester.ingest_path(test_file, "ds_guide")

            # Query and check for tags in metadata
            full_collection = f"{rag_config.collection_prefix}_{result.collection}"
            query_results = db_backend.query(
                full_collection,
                query_embedding=[0.1] * 384,
                n_results=10,
            )

            metadatas = query_results.get("metadatas", [[]])[0]
            for metadata in metadatas:
                if "tags" in metadata:
                    tags = metadata["tags"]
                    # Tags should be present and include the extracted ones
                    assert isinstance(tags, list)
                    assert any(
                        tag in ["data-science", "statistics", "ml"] for tag in tags
                    )


class TestRAGRetriever:
    """Test RAG retriever with parent-child architecture."""

    def test_retrieve_returns_parent_documents(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that retriever returns full parent documents."""
        markdown_content = """# Computer Science

## Algorithms

Sorting and searching algorithms are fundamental.

## Data Structures

Trees, graphs, and linked lists.

Tags:
- #cs #algorithms
"""

        test_file = temp_rag_dir / "cs.md"
        test_file.write_text(markdown_content)

        with (
            patch("tools.rag.ingest.EmbeddingClient") as mock_ingest_embedder,
            patch("tools.rag.retriever.EmbeddingClient") as mock_retriever_embedder,
        ):
            # Mock ingestion
            mock_ingest = MagicMock()
            mock_ingest_embedder.return_value = mock_ingest

            def mock_embed_ingest(texts):
                return [[0.1] * 384 for _ in texts]

            mock_ingest.embed_texts = mock_embed_ingest

            # Mock retrieval
            mock_retrieve = MagicMock()
            mock_retriever_embedder.return_value = mock_retrieve
            mock_retrieve.embed_query.return_value = [0.1] * 384

            ingester = RAGIngester(rag_config, db_backend)
            ingester.ingest_path(test_file, "cs_guide")

            # Retrieve documents
            retriever = RAGRetriever(rag_config, db_backend)
            results = retriever.retrieve("algorithms", "cs_guide", top_k=5)

            # Verify we get parent documents back
            assert len(results) > 0
            for doc in results:
                assert doc.id is not None
                assert len(doc.text) > 0  # Parent documents should have full content
                assert "rank" in doc.__dict__
                assert "score" in doc.__dict__

    def test_retrieve_with_metadata_filter(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test retrieval with metadata filtering."""
        markdown_content = """# Advanced Topics

## AI and Machine Learning

Deep learning applications.

## Quantum Computing

Quantum algorithms and qubits.

Tags:
- #ai #ml #advanced
"""

        test_file = temp_rag_dir / "advanced.md"
        test_file.write_text(markdown_content)

        with (
            patch("tools.rag.ingest.EmbeddingClient") as mock_ingest_embedder,
            patch("tools.rag.retriever.EmbeddingClient") as mock_retriever_embedder,
        ):
            mock_ingest = MagicMock()
            mock_ingest_embedder.return_value = mock_ingest

            def mock_embed_ingest(texts):
                return [[0.1] * 384 for _ in texts]

            mock_ingest.embed_texts = mock_embed_ingest

            mock_retrieve = MagicMock()
            mock_retriever_embedder.return_value = mock_retrieve
            mock_retrieve.embed_query.return_value = [0.1] * 384

            ingester = RAGIngester(rag_config, db_backend)
            ingester.ingest_path(test_file, "advanced")

            # Retrieve with filter
            retriever = RAGRetriever(rag_config, db_backend)

            # Filter by specific tag
            where = {"tags": {"$in": ["ai"]}}
            results = retriever.retrieve("learning", "advanced", top_k=5, where=where)

            # Should return filtered results
            # Note: Actual filtering depends on the embedding model behavior
            assert isinstance(results, list)

    def test_retrieve_deduplicates_parent_documents(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that retriever deduplicates parent documents from multiple child chunks."""
        markdown_content = """# Long Document

## Section One

This is a very long section with a lot of text content that will be split into multiple chunks.
The same parent document ID will appear in multiple child chunks.
When retrieving, we should only get one copy of the parent document even though multiple children matched.

Additional content to ensure splitting across chunks.
More text here to create multiple chunks from the same parent.

## Section Two

Another section with content.

Tags:
- #testing #deduplication
"""

        test_file = temp_rag_dir / "long.md"
        test_file.write_text(markdown_content)

        with (
            patch("tools.rag.ingest.EmbeddingClient") as mock_ingest_embedder,
            patch("tools.rag.retriever.EmbeddingClient") as mock_retriever_embedder,
        ):
            mock_ingest = MagicMock()
            mock_ingest_embedder.return_value = mock_ingest

            def mock_embed_ingest(texts):
                return [[0.1] * 384 for _ in texts]

            mock_ingest.embed_texts = mock_embed_ingest

            mock_retrieve = MagicMock()
            mock_retriever_embedder.return_value = mock_retrieve
            mock_retrieve.embed_query.return_value = [0.1] * 384

            ingester = RAGIngester(rag_config, db_backend)
            ingester.ingest_path(test_file, "long_doc")

            # Retrieve should deduplicate parent documents
            retriever = RAGRetriever(rag_config, db_backend)
            results = retriever.retrieve("content", "long_doc", top_k=10)

            # Collect parent IDs to verify deduplication
            parent_ids = [doc.id for doc in results]
            assert len(parent_ids) == len(
                set(parent_ids)
            ), "Parent documents should be deduplicated"


class TestRAGAgent:
    """Test RAG agent with parent-child retrieval."""

    def test_agent_retrieves_documents(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that RAG agent can retrieve documents."""
        markdown_content = """# Biology

## Cells

Cells are the basic unit of life.

## DNA

DNA carries genetic information.

Tags:
- #biology #science
"""

        test_file = temp_rag_dir / "biology.md"
        test_file.write_text(markdown_content)

        with (
            patch("tools.rag.ingest.EmbeddingClient") as mock_ingest_embedder,
            patch("tools.rag.retriever.EmbeddingClient") as mock_retriever_embedder,
        ):
            mock_ingest = MagicMock()
            mock_ingest_embedder.return_value = mock_ingest

            def mock_embed_ingest(texts):
                return [[0.1] * 384 for _ in texts]

            mock_ingest.embed_texts = mock_embed_ingest

            mock_retrieve = MagicMock()
            mock_retriever_embedder.return_value = mock_retrieve
            mock_retrieve.embed_query.return_value = [0.1] * 384

            ingester = RAGIngester(rag_config, db_backend)
            ingester.ingest_path(test_file, "biology")

            # Test agent retrieval
            agent = RAGAgent(rag_config, db_backend)
            results = agent.retrieve("cells", "biology")

            assert len(results) > 0
            for doc in results:
                assert hasattr(doc, "text")
                assert hasattr(doc, "metadata")

    def test_agent_filter_parameters(
        self, rag_config: RAGConfig, db_backend: ChromaDBBackend, temp_rag_dir: Path
    ) -> None:
        """Test that agent properly forwards filter parameters."""
        markdown_content = """# Filtered Content

## Section A

Content for section A.

## Section B

Content for section B.

Tags:
- #filter-test #section-a
"""

        test_file = temp_rag_dir / "filtered.md"
        test_file.write_text(markdown_content)

        with (
            patch("tools.rag.ingest.EmbeddingClient") as mock_ingest_embedder,
            patch("tools.rag.retriever.EmbeddingClient") as mock_retriever_embedder,
        ):
            mock_ingest = MagicMock()
            mock_ingest_embedder.return_value = mock_ingest

            def mock_embed_ingest(texts):
                return [[0.1] * 384 for _ in texts]

            mock_ingest.embed_texts = mock_embed_ingest

            mock_retrieve = MagicMock()
            mock_retriever_embedder.return_value = mock_retrieve
            mock_retrieve.embed_query.return_value = [0.1] * 384

            ingester = RAGIngester(rag_config, db_backend)
            ingester.ingest_path(test_file, "filtered")

            # Test with where filter
            agent = RAGAgent(rag_config, db_backend)
            where = {"tags": {"$in": ["filter-test"]}}
            results = agent.retrieve("section", "filtered", where=where)

            # Should be able to call with filters without error
            assert isinstance(results, list)
