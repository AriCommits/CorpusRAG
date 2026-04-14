"""Document ingestion for RAG."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Optional

from db import DatabaseBackend

from .config import RAGConfig
from .embeddings import EmbeddingClient


@dataclass(frozen=True)
class IngestResult:
    """Result of document ingestion."""

    collection: str
    files_indexed: int
    chunks_indexed: int


class RAGIngester:
    """Ingest documents into RAG collections."""

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        """Initialize RAG ingester.

        Args:
            config: RAG configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        self.embedder = EmbeddingClient(config)

    def ingest_path(
        self, path: Path | str, collection: str, max_file_size_mb: int = 1000
    ) -> IngestResult:
        """Ingest documents from a file or directory.

        Args:
            path: Path to file or directory
            collection: Collection name
            max_file_size_mb: Maximum file size in MB (default: 1000)

        Returns:
            IngestResult with statistics

        Raises:
            ValueError: If file size exceeds limit
        """
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Path does not exist: {source}")

        # Validate file size
        max_size_bytes = max_file_size_mb * 1024 * 1024
        if source.is_file():
            file_size = source.stat().st_size
            if file_size > max_size_bytes:
                raise ValueError(
                    f"File '{source.name}' exceeds maximum size of {max_file_size_mb}MB "
                    f"({file_size / (1024 * 1024):.1f}MB)"
                )
        else:
            # For directories, check each file
            for file_path in source.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    file_size = file_path.stat().st_size
                    if file_size > max_size_bytes:
                        raise ValueError(
                            f"File '{file_path.name}' exceeds maximum size of {max_file_size_mb}MB "
                            f"({file_size / (1024 * 1024):.1f}MB)"
                        )

        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Create collection if it doesn't exist
        if not self.db.collection_exists(full_collection):
            self.db.create_collection(full_collection)

        # Collect all files to process
        files = list(self._iter_source_files(source))

        document_texts: list[str] = []
        metadata_list: list[dict[str, object]] = []
        ids: list[str] = []
        files_indexed = 0

        for file_path in files:
            # Read file content
            content = self._read_file(file_path)
            if not content.strip():
                continue

            # Chunk the content
            chunks = self._chunk_text(content)
            if not chunks:
                continue

            files_indexed += 1

            # Create document for each chunk
            relative_path = (
                str(file_path.relative_to(source)) if file_path != source else file_path.name
            )

            for i, chunk_text in enumerate(chunks):
                doc_id = self._build_chunk_id(full_collection, relative_path, i, chunk_text)
                document_texts.append(chunk_text)
                metadata_list.append(
                    {
                        "source_file": relative_path,
                        "chunk_index": i,
                        "collection_name": collection,
                    }
                )
                ids.append(doc_id)

        # Add documents to collection
        chunks_indexed = len(document_texts)
        if document_texts:
            embeddings = self.embedder.embed_texts(document_texts)
            self.db.add_documents(
                full_collection,
                documents=document_texts,
                embeddings=embeddings,
                metadata=metadata_list,
                ids=ids,
            )

        return IngestResult(
            collection=collection,
            files_indexed=files_indexed,
            chunks_indexed=chunks_indexed,
        )

    def _iter_source_files(self, path: Path) -> list[Path]:
        """Iterate over source files to ingest.

        Args:
            path: Root path to search

        Returns:
            List of file paths
        """
        if path.is_file():
            if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                return [path]
            return []

        # Recursively find all supported files
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(path.rglob(f"*{ext}"))

        return sorted(files)

    def _read_file(self, file_path: Path) -> str:
        """Read file content.

        Args:
            file_path: Path to file

        Returns:
            File content as text
        """
        suffix = file_path.suffix.lower()

        if suffix in {".md", ".txt"}:
            return file_path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            return self._read_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def _read_pdf(self, file_path: Path) -> str:
        """Read PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "pypdf is required for PDF ingestion. Install with: pip install pypdf"
            )

        reader = pypdf.PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        return "\n\n".join(pages)

    def _chunk_text(self, text: str) -> list[str]:
        """Chunk text into smaller pieces.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        chunk_size = self.config.chunking.size
        overlap = self.config.chunking.overlap

        # Simple character-based chunking
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if chunk.strip():
                chunks.append(chunk)

            start = end - overlap

            # Prevent infinite loop
            if overlap >= chunk_size:
                break

        return chunks

    def _build_chunk_id(
        self, collection: str, source_file: str, chunk_index: int, text: str
    ) -> str:
        """Build deterministic chunk ID.

        Args:
            collection: Collection name
            source_file: Source file name
            chunk_index: Index of chunk within file
            text: Chunk text

        Returns:
            Chunk ID hash
        """
        content = f"{collection}::{source_file}::{chunk_index}::{text}"
        return sha256(content.encode("utf-8")).hexdigest()[:16]
