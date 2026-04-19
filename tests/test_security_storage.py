"""Security tests for LocalFileStore path traversal protection."""

import tempfile
from pathlib import Path

import pytest
from langchain_core.documents import Document

from src.tools.rag.pipeline.storage import LocalFileStore
from utils.security import sanitize_filename


class TestPathTraversalProtection:
    """Tests for path traversal attack prevention."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalFileStore(tmpdir)

    def test_doc_id_sanitization_removes_traversal(self, store):
        """LocalFileStore sanitizes doc_id with .. traversal."""
        doc = Document(page_content="test", metadata={})
        # Dangerous IDs are sanitized, not rejected
        store.put("../malicious", doc)

        # The sanitized version should be stored
        sanitized_id = sanitize_filename("../malicious")
        retrieved = store.get(sanitized_id)
        assert retrieved is not None

    def test_doc_id_sanitization_removes_path_separators(self, store):
        """LocalFileStore sanitizes doc_id with path separators."""
        doc = Document(page_content="test", metadata={})
        store.put("path/to/file", doc)

        # Should be retrievable with sanitized ID
        sanitized_id = sanitize_filename("path/to/file")
        retrieved = store.get(sanitized_id)
        assert retrieved is not None

    def test_valid_doc_id_stored_and_retrieved(self, store):
        """Valid document IDs are stored and retrieved successfully."""
        doc = Document(page_content="test content", metadata={"key": "value"})
        store.put("valid_doc_id", doc)

        retrieved = store.get("valid_doc_id")
        assert retrieved is not None
        assert retrieved.page_content == "test content"
        assert retrieved.metadata["key"] == "value"

    def test_uuid_doc_ids_work(self, store):
        """UUID-format document IDs work correctly."""
        import uuid

        doc_id = str(uuid.uuid4())
        doc = Document(page_content="test", metadata={})
        store.put(doc_id, doc)

        retrieved = store.get(doc_id)
        assert retrieved is not None
        assert retrieved.page_content == "test"

    def test_special_characters_sanitized(self, store):
        """Special characters in doc_id are sanitized."""
        doc = Document(page_content="test", metadata={})
        dangerous_id = "doc;rm -rf|test"
        store.put(dangerous_id, doc)

        # Should be sanitized
        sanitized_id = sanitize_filename(dangerous_id)
        retrieved = store.get(sanitized_id)
        assert retrieved is not None

    def test_list_keys_returns_valid_ids(self, store):
        """list_keys returns only valid stored IDs."""
        store.put("doc1", Document(page_content="test1", metadata={}))
        store.put("doc2", Document(page_content="test2", metadata={}))

        keys = store.list_keys()
        assert "doc1" in keys
        assert "doc2" in keys


class TestFilenameMetadataSanitization:
    """Tests for filename metadata sanitization."""

    def test_filename_sanitization_removes_path_separators(self):
        """Path separators in filenames are sanitized."""
        dangerous_name = "file/path\\to/file.md"
        sanitized = sanitize_filename(dangerous_name)

        # Should not contain path separators
        assert "/" not in sanitized
        assert "\\" not in sanitized
        # They should be replaced with underscores
        assert "_" in sanitized

    def test_filename_sanitization_removes_traversal(self):
        """Directory traversal attempts are sanitized."""
        traversal_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "...file.txt",
        ]

        for name in traversal_names:
            sanitized = sanitize_filename(name)
            # Should not be able to traverse
            assert ".." not in sanitized
            assert "/" not in sanitized
            assert "\\" not in sanitized

    def test_filename_sanitization_preserves_valid_names(self):
        """Valid filenames are preserved."""
        valid_names = [
            "my_file.md",
            "document-2024.txt",
            "data123.json",
        ]

        for name in valid_names:
            sanitized = sanitize_filename(name)
            assert sanitized == name

    def test_filename_removes_special_chars(self):
        """Special characters that are invalid in filenames are removed."""
        special_names = [
            "file:invalid.txt",  # colon
            "file*invalid.txt",   # asterisk
            "file?invalid.txt",   # question mark
            "file\"quoted\".txt",  # quotes
            "file<angle>.txt",     # angle brackets
            "file|pipe.txt",       # pipe
        ]

        for name in special_names:
            sanitized = sanitize_filename(name)
            # All special chars should be replaced
            assert ":" not in sanitized
            assert "*" not in sanitized
            assert "?" not in sanitized
            assert '"' not in sanitized
            assert "<" not in sanitized
            assert ">" not in sanitized
            assert "|" not in sanitized
