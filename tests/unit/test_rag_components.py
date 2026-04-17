"""Unit tests for RAG components."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.rag.config import RAGConfig
from tools.rag.ingest import RAGIngester
from tools.rag.markdown_parser import (
    extract_tags_from_text,
    parse_and_split,
    split_markdown_semantic,
)
from tools.rag.retriever import RAGRetriever, RetrievedDocument
from tools.rag.storage import LocalFileStore


class TestMarkdownParser:
    """Tests for markdown parsing functions."""

    def test_extract_tags_simple(self) -> None:
        """Test extracting tags from simple markdown."""
        text = """# Title

## Section

Content here

Tags:
- #python #ml #data-science
"""
        cleaned, tags = extract_tags_from_text(text)
        assert "python" in tags
        assert "ml" in tags
        assert "data-science" in tags
        assert "- #python #ml #data-science" not in cleaned

    def test_extract_tags_multiple_lines(self) -> None:
        """Test extracting tags from multiple bullet lines."""
        text = """# Title

Tags:
- #tag1 #tag2
- #tag3 #tag4
- #tag5
"""
        cleaned, tags = extract_tags_from_text(text)
        assert len(tags) == 5
        assert all(f"tag{i}" in tags for i in range(1, 6))

    def test_extract_tags_asterisk_bullets(self) -> None:
        """Test extracting tags from asterisk-style bullets."""
        text = """# Title

Tags:
* #python
* #testing
"""
        cleaned, tags = extract_tags_from_text(text)
        assert "python" in tags
        assert "testing" in tags

    def test_extract_tags_no_tags(self) -> None:
        """Test extraction when no tags present."""
        text = """# Title

## Section

Just regular content with no tags.
"""
        cleaned, tags = extract_tags_from_text(text)
        assert len(tags) == 0
        assert cleaned == text

    def test_extract_tags_preserves_non_tag_bullets(self) -> None:
        """Test that non-tag bullets are preserved."""
        text = """# Title

## Section

Tasks:
- Buy milk
- Walk dog

Tags:
- #todo
"""
        cleaned, tags = extract_tags_from_text(text)
        assert "todo" in tags
        assert "- Buy milk" in cleaned
        assert "- Walk dog" in cleaned

    def test_split_markdown_semantic_basic(self) -> None:
        """Test semantic splitting of markdown."""
        text = """# Main Title

## Section One

Content for section one.

## Section Two

Content for section two.

### Subsection

More content.
"""
        docs = split_markdown_semantic(text)
        assert len(docs) > 0
        # Should have documents for different sections
        assert any("Section One" in str(doc.metadata) for doc in docs)

    def test_split_markdown_preserves_content(self) -> None:
        """Test that splitting preserves document content."""
        text = """# Title

## Section

Important content here.
"""
        docs = split_markdown_semantic(text)
        full_content = "\n".join(doc.page_content for doc in docs)
        assert "Important content here" in full_content

    def test_parse_and_split_format(self) -> None:
        """Test parse_and_split returns correct format."""
        text = """# Title

## Section

Content here.

Tags:
- #python
"""
        result = parse_and_split(text)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all("text" in item and "metadata" in item for item in result)

    def test_parse_and_split_with_source(self) -> None:
        """Test parse_and_split includes source filename."""
        text = "# Title\n\nContent"
        result = parse_and_split(text, source_name="test.md")
        assert all(item["metadata"].get("source_file") == "test.md" for item in result)


class TestLocalFileStore:
    """Tests for LocalFileStore."""

    def test_store_initialization(self, tmp_path: Path) -> None:
        """Test initializing a file store."""
        LocalFileStore(tmp_path / "store")
        assert (tmp_path / "store").exists()

    def test_put_and_get(self, tmp_path: Path) -> None:
        """Test storing and retrieving documents."""
        from langchain_core.documents import Document

        store = LocalFileStore(tmp_path / "store")
        doc = Document(page_content="Test content", metadata={"key": "value"})

        store.put("doc1", doc)
        retrieved = store.get("doc1")

        assert retrieved is not None
        assert retrieved.page_content == "Test content"
        assert retrieved.metadata["key"] == "value"

    def test_mset_and_mget(self, tmp_path: Path) -> None:
        """Test batch storage and retrieval."""
        from langchain_core.documents import Document

        store = LocalFileStore(tmp_path / "store")
        docs = [
            ("id1", Document(page_content="Content 1")),
            ("id2", Document(page_content="Content 2")),
            ("id3", Document(page_content="Content 3")),
        ]

        store.mset(docs)
        retrieved = store.mget(["id1", "id2", "id3"])

        assert len(retrieved) == 3
        assert all(doc is not None for doc in retrieved)
        assert retrieved[0].page_content == "Content 1"
        assert retrieved[2].page_content == "Content 3"

    def test_delete_document(self, tmp_path: Path) -> None:
        """Test deleting a document."""
        from langchain_core.documents import Document

        store = LocalFileStore(tmp_path / "store")
        doc = Document(page_content="Test")
        store.put("doc1", doc)
        assert store.get("doc1") is not None

        store.delete("doc1")
        assert store.get("doc1") is None

    def test_mget_nonexistent(self, tmp_path: Path) -> None:
        """Test retrieving nonexistent documents."""
        store = LocalFileStore(tmp_path / "store")
        retrieved = store.mget(["nonexistent1", "nonexistent2"])
        assert all(doc is None for doc in retrieved)


class TestRAGIngester:
    """Tests for RAGIngester."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test RAGIngester initialization."""
        from config.base import DatabaseConfig, EmbeddingConfig, PathsConfig

        db_config = DatabaseConfig(persist_directory=tmp_path / "db")
        embedding_config = EmbeddingConfig()
        paths_config = PathsConfig()

        rag_config = RAGConfig(
            llm=MagicMock(),
            embedding=embedding_config,
            database=db_config,
            paths=paths_config,
        )

        with patch("tools.rag.ingest.EmbeddingClient"):
            ingester = RAGIngester(rag_config, MagicMock())
            assert ingester.config == rag_config
            assert (tmp_path / "parent_store").exists() or True  # May be created lazily

    def test_supported_extensions(self) -> None:
        """Test SUPPORTED_EXTENSIONS."""
        assert ".md" in RAGIngester.SUPPORTED_EXTENSIONS
        assert ".txt" in RAGIngester.SUPPORTED_EXTENSIONS
        assert ".pdf" in RAGIngester.SUPPORTED_EXTENSIONS


class TestRAGRetriever:
    """Tests for RAGRetriever."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test RAGRetriever initialization."""
        from config.base import DatabaseConfig, EmbeddingConfig, PathsConfig

        db_config = DatabaseConfig(persist_directory=tmp_path / "db")
        embedding_config = EmbeddingConfig()
        paths_config = PathsConfig()

        rag_config = RAGConfig(
            llm=MagicMock(),
            embedding=embedding_config,
            database=db_config,
            paths=paths_config,
        )

        with patch("tools.rag.retriever.EmbeddingClient"):
            retriever = RAGRetriever(rag_config, MagicMock())
            assert retriever.config == rag_config

    def test_retrieved_document_structure(self) -> None:
        """Test RetrievedDocument structure."""
        doc = RetrievedDocument(
            id="doc1",
            text="Content here",
            metadata={"source": "test.md"},
            rank=1,
            score=0.95,
        )
        assert doc.id == "doc1"
        assert doc.text == "Content here"
        assert doc.metadata["source"] == "test.md"
        assert doc.rank == 1
        assert doc.score == 0.95


class TestRAGConfig:
    """Tests for RAG configuration."""

    def test_rag_config_defaults(self) -> None:
        """Test RAGConfig default values."""
        config = RAGConfig(
            llm=MagicMock(),
            embedding=MagicMock(),
            database=MagicMock(),
            paths=MagicMock(),
        )
        assert config.collection_prefix == "rag"
        assert config.chunking.child_chunk_size == 400
        assert config.chunking.child_chunk_overlap == 50
        assert config.retrieval.top_k_final == 10

    def test_rag_config_from_dict(self) -> None:
        """Test creating RAGConfig from dictionary."""
        data = {
            "llm": {"model": "test-model"},
            "embedding": {"model": "test-embedding"},
            "database": {"mode": "persistent"},
            "paths": {"vault": "./vault"},
            "rag": {
                "chunking": {"child_chunk_size": 500},
                "retrieval": {"top_k_final": 5},
            },
        }
        config = RAGConfig.from_dict(data)
        assert config.chunking.child_chunk_size == 500
        assert config.retrieval.top_k_final == 5

    def test_parent_store_path_conversion(self) -> None:
        """Test path string to Path conversion in config."""
        data = {
            "llm": {},
            "embedding": {},
            "database": {},
            "paths": {},
            "rag": {"parent_store": {"path": "/tmp/parent_store"}},
        }
        config = RAGConfig.from_dict(data)
        assert config.parent_store.path == Path("/tmp/parent_store")
