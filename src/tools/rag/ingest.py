"""Document ingestion for RAG with parent-child retrieval architecture."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from db import DatabaseBackend

from .config import RAGConfig
from .embeddings import EmbeddingClient
from .markdown_parser import split_markdown_semantic
from .storage import LocalFileStore


@dataclass(frozen=True)
class IngestResult:
    """Result of document ingestion."""

    collection: str
    files_indexed: int
    chunks_indexed: int


class RAGIngester:
    """Ingest documents into RAG collections using parent-child retrieval architecture."""

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

        # Initialize parent document store
        self.config.parent_store.path.mkdir(parents=True, exist_ok=True)
        self.parent_store = LocalFileStore(str(self.config.parent_store.path))

        # Initialize child text splitter
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunking.child_chunk_size,
            chunk_overlap=self.config.chunking.child_chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def ingest_path(
        self, path: Path | str, collection: str, max_file_size_mb: int = 1000
    ) -> IngestResult:
        """Ingest documents from a file or directory.

        Uses semantic markdown splitting to create parent documents, then creates
        child chunks for vector search while maintaining parent-child linkage.
        Implements incremental sync by checking content hashes.

        Args:
            path: Path to file or directory
            collection: Collection name
            max_file_size_mb: Maximum file size in MB (default: 1000)

        Returns:
            IngestResult with statistics

        Raises:
            ValueError: If file size exceeds limit
        """
        source_original = Path(path).expanduser()

        # Check for symlinks to prevent path traversal attacks
        if source_original.is_symlink():
            raise ValueError(
                f"Symlinks are not allowed for security reasons: {source_original}. "
                "Please use the actual file path instead."
            )

        source = source_original.resolve()
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
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
                ):
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

        child_documents: list[str] = []
        child_metadata: list[dict[str, object]] = []
        child_ids: list[str] = []
        files_indexed = 0
        chunks_indexed = 0

        for file_path in files:
            # Read file content
            content = self._read_file(file_path)
            if not content.strip():
                continue

            relative_path = (
                str(file_path.relative_to(source))
                if file_path != source
                else file_path.name
            )

            # Compute hash for incremental sync
            file_hash = sha256(content.encode("utf-8")).hexdigest()

            # Check if file already exists in DB with same hash
            existing_metadatas = self.db.get_metadata_by_filter(
                full_collection, where={"source_file": relative_path}, limit=1
            )

            if existing_metadatas:
                existing_hash = existing_metadatas[0].get("file_hash")
                if existing_hash == file_hash:
                    # File unchanged, skip
                    continue
                else:
                    # File modified, delete old version from DB and parent store
                    self.db.delete_by_metadata(
                        full_collection, where={"source_file": relative_path}
                    )
                    self.parent_store.delete_by_metadata(
                        lambda m: m.get("source_file") == relative_path
                    )

            files_indexed += 1

            # Split markdown semantically (parent documents)
            parent_docs = split_markdown_semantic(content)

            for parent_idx, parent_doc in enumerate(parent_docs):
                # Create parent with unique ID
                parent_id = str(uuid4())
                parent_metadata = (
                    dict(parent_doc.metadata) if parent_doc.metadata else {}
                )
                parent_metadata["source_file"] = relative_path
                parent_metadata["parent_index"] = parent_idx
                parent_metadata["file_hash"] = file_hash

                # Store parent document in document store
                parent_langchain_doc = Document(
                    page_content=parent_doc.page_content,
                    metadata=parent_metadata,
                )
                self.parent_store.mset([(parent_id, parent_langchain_doc)])

                # Split parent into children for vector search
                child_docs = self.child_splitter.split_text(parent_doc.page_content)

                for child_idx, child_text in enumerate(child_docs):
                    if not child_text.strip():
                        continue

                    child_id = self._build_chunk_id(
                        full_collection, parent_id, child_idx
                    )
                    child_documents.append(child_text)

                    # Child metadata includes parent linkage
                    metadata = dict(parent_metadata)
                    metadata["parent_id"] = parent_id
                    metadata["child_index"] = child_idx
                    metadata["collection_name"] = collection
                    child_metadata.append(metadata)
                    child_ids.append(child_id)
                    chunks_indexed += 1

        # Add child documents to collection with embeddings
        if child_documents:
            embeddings = self.embedder.embed_texts(child_documents)
            self.db.add_documents(
                full_collection,
                documents=child_documents,
                embeddings=embeddings,
                metadata=child_metadata,
                ids=child_ids,
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

    def _build_chunk_id(self, collection: str, parent_id: str, child_index: int) -> str:
        """Build deterministic chunk ID for child document.

        Args:
            collection: Collection name
            parent_id: Parent document ID
            child_index: Index of child within parent

        Returns:
            Chunk ID hash
        """
        content = f"{collection}::{parent_id}::{child_index}"
        return sha256(content.encode("utf-8")).hexdigest()[:16]
