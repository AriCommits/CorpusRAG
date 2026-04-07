"""Document ingestion for RAG."""

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Optional

from corpus_callosum.db import DatabaseBackend, Document

from .config import RAGConfig


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

    def ingest_path(self, path: Path | str, collection: str) -> IngestResult:
        """Ingest documents from a file or directory.

        Args:
            path: Path to file or directory
            collection: Collection name

        Returns:
            IngestResult with statistics
        """
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Path does not exist: {source}")

        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Create collection if it doesn't exist
        if not self.db.collection_exists(full_collection):
            self.db.create_collection(full_collection)

        # Collect all files to process
        files = list(self._iter_source_files(source))
        
        documents = []
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
            relative_path = str(file_path.relative_to(source)) if file_path != source else file_path.name
            
            for i, chunk_text in enumerate(chunks):
                doc_id = self._build_chunk_id(full_collection, relative_path, i, chunk_text)
                
                documents.append(
                    Document(
                        id=doc_id,
                        content=chunk_text,
                        metadata={
                            "source_file": relative_path,
                            "chunk_index": i,
                            "collection_name": collection,
                        },
                    )
                )

        # Add documents to collection
        chunks_indexed = len(documents)
        if documents:
            self.db.add_documents(full_collection, documents)

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
                "pypdf is required for PDF ingestion. "
                "Install with: pip install pypdf"
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
        chunk_size = self.config.chunking.chunk_size
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
        return sha1(content.encode("utf-8")).hexdigest()[:16]
