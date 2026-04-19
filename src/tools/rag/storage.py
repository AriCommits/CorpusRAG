"""Local file-based storage for parent documents."""

import json
from pathlib import Path

from langchain_core.documents import Document


class LocalFileStore:
    """Simple local file-based document store for parent documents.

    Stores Document objects as JSON files, with one file per document ID.
    """

    def __init__(self, path: str | Path):
        """Initialize file store.

        Args:
            path: Directory path for storing documents
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def mset(self, items: list[tuple[str, Document]]) -> None:
        """Store multiple documents.

        Args:
            items: List of (id, document) tuples
        """
        for doc_id, doc in items:
            self._save_document(doc_id, doc)

    def mget(self, keys: list[str]) -> list[Document | None]:
        """Retrieve multiple documents.

        Args:
            keys: List of document IDs

        Returns:
            List of documents or None for missing IDs
        """
        return [self._load_document(key) for key in keys]

    def get(self, key: str) -> Document | None:
        """Retrieve a single document.

        Args:
            key: Document ID

        Returns:
            Document or None if not found
        """
        return self._load_document(key)

    def put(self, key: str, value: Document) -> None:
        """Store a single document.

        Args:
            key: Document ID
            value: Document to store
        """
        self._save_document(key, value)

    def delete(self, key: str) -> None:
        """Delete a document.

        Args:
            key: Document ID
        """
        file_path = self.path / f"{key}.json"
        if file_path.exists():
            file_path.unlink()

    def delete_by_metadata(self, filter_func: callable) -> int:
        """Delete documents that match the filter function.

        Args:
            filter_func: Function that takes metadata dict and returns True to delete

        Returns:
            Number of deleted documents
        """
        deleted_count = 0
        keys = self.list_keys()
        for key in keys:
            doc = self.get(key)
            if doc and filter_func(doc.metadata):
                self.delete(key)
                deleted_count += 1
        return deleted_count

    def list_keys(self) -> list[str]:
        """List all document IDs in store.

        Returns:
            List of document IDs
        """
        return [f.stem for f in self.path.glob("*.json")]

    def mget_all(self) -> list[tuple[str, Document]]:
        """Retrieve all documents in store.

        Returns:
            List of (id, document) tuples
        """
        keys = self.list_keys()
        docs = self.mget(keys)
        return [(k, d) for k, d in zip(keys, docs) if d is not None]

    def _save_document(self, doc_id: str, doc: Document) -> None:
        """Save a document as JSON.

        Args:
            doc_id: Document ID (used as filename)
            doc: Document to save
        """
        file_path = self.path / f"{doc_id}.json"
        doc_data = {
            "page_content": doc.page_content,
            "metadata": dict(doc.metadata) if doc.metadata else {},
        }
        file_path.write_text(json.dumps(doc_data, indent=2, default=str), encoding="utf-8")

    def _load_document(self, doc_id: str) -> Document | None:
        """Load a document from JSON.

        Args:
            doc_id: Document ID (filename without .json)

        Returns:
            Document or None if not found
        """
        file_path = self.path / f"{doc_id}.json"
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return Document(
                page_content=data.get("page_content", ""),
                metadata=data.get("metadata", {}),
            )
        except Exception:
            return None
