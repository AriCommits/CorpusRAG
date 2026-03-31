"""Document ingestion for CorpusCallosum."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer

from .chroma import create_chroma_client
from .config import Config, get_config

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


@dataclass(slots=True, frozen=True)
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class IngestResult:
    collection: str
    files_indexed: int
    chunks_indexed: int


class Ingester:
    """Loads source files, chunks content, and writes vectors to ChromaDB."""

    def __init__(
        self,
        *,
        config: Config | None = None,
        chroma_client: Any | None = None,
        embedding_model: SentenceTransformer | None = None,
    ) -> None:
        self.config = config or get_config()
        self.client = chroma_client or create_chroma_client(self.config)
        self._embedding_model = embedding_model

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.config.embedding.model)
        return self._embedding_model

    def ingest_path(self, path: str | Path, collection_name: str) -> IngestResult:
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Path does not exist: {source}")
        if not collection_name.strip():
            raise ValueError("collection_name cannot be empty")

        # Security: Prevent obvious directory traversal attacks
        # Don't allow paths with parent directory references that would escape intended directories
        # We allow reasonable use of .. but prevent escapes that would go outside intended boundaries
        resolved_path = source.resolve()
        # Check for any attempt to access sensitive system directories
        sensitive_paths = ["/etc", "/var", "/usr", "/root", "/proc", "/sys"]
        for sensitive in sensitive_paths:
            try:
                resolved_path.relative_to(sensitive)
                raise ValueError(
                    f"Path {source} attempts to access sensitive directory {sensitive}. "
                    f"This is not allowed for security reasons."
                )
            except ValueError:
                # This is expected if the path is NOT under the sensitive directory
                pass

        # Additional check: prevent paths that try to escape by going up too many levels
        # This is a basic heuristic - if we have more than 5 consecutive .. components,
        # it's likely an attempt to traverse excessively
        path_str = str(source)
        if path_str.count("/../") > 3 or (path_str.endswith("/..") and path_str.count("/..") > 3):
            raise ValueError(
                f"Path {source} contains excessive parent directory references that may indicate "
                f"an attempt to traverse directories maliciously."
            )

        files = list(self._iter_source_files(source))
        chunk_records: list[ChunkRecord] = []
        files_indexed = 0

        for file_path in files:
            raw_text = self._read_file_text(file_path)
            if not raw_text.strip():
                continue

            chunks = self._chunk_text(raw_text)
            if not chunks:
                continue

            files_indexed += 1
            source_file = self._relative_source_name(source, file_path)
            for chunk_index, chunk_text in enumerate(chunks):
                chunk_id = self._build_chunk_id(
                    collection_name=collection_name,
                    source_file=source_file,
                    chunk_index=chunk_index,
                    text=chunk_text,
                )
                chunk_records.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        metadata={
                            "source_file": source_file,
                            "chunk_index": chunk_index,
                            "collection_name": collection_name,
                        },
                    )
                )

        if chunk_records:
            self._upsert_chunks(collection_name=collection_name, chunks=chunk_records)

        return IngestResult(
            collection=collection_name,
            files_indexed=files_indexed,
            chunks_indexed=len(chunk_records),
        )

    def _iter_source_files(self, source: Path) -> list[Path]:
        if source.is_file():
            return [source] if source.suffix.lower() in SUPPORTED_EXTENSIONS else []

        discovered = [
            file_path
            for file_path in source.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        discovered.sort()
        return discovered

    def _relative_source_name(self, source: Path, file_path: Path) -> str:
        if source.is_file():
            return file_path.name
        return str(file_path.relative_to(source))

    def _read_file_text(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in {".md", ".txt"}:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            return self._read_pdf_text(file_path)
        return ""

    def _read_pdf_text(self, file_path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PDF ingestion requires pypdf. Install with: pip install pypdf"
            ) from exc

        reader = PdfReader(str(file_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        if not words:
            return []

        size = self.config.chunking.size
        overlap = self.config.chunking.overlap
        step = size - overlap

        if len(words) <= size:
            return [" ".join(words)]

        chunks: list[str] = []
        for start in range(0, len(words), step):
            end = start + size
            chunk_words = words[start:end]
            if not chunk_words:
                break
            chunks.append(" ".join(chunk_words))
            if end >= len(words):
                break
        return chunks

    def _build_chunk_id(
        self,
        *,
        collection_name: str,
        source_file: str,
        chunk_index: int,
        text: str,
    ) -> str:
        digest = sha1(text.encode("utf-8")).hexdigest()[:12]
        return f"{collection_name}:{source_file}:{chunk_index}:{digest}"

    def _upsert_chunks(self, *, collection_name: str, chunks: list[ChunkRecord]) -> None:
        collection = self.client.get_or_create_collection(name=collection_name)

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        embeddings = self.embedding_model.encode(documents, show_progress_bar=False).tolist()

        if hasattr(collection, "upsert"):
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            return

        collection.delete(ids=ids)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB")
    parser.add_argument("--path", required=True, help="File or directory to ingest")
    parser.add_argument("--collection", required=True, help="Target collection name")
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    ingester = Ingester()
    result = ingester.ingest_path(path=args.path, collection_name=args.collection)
    print(
        "Ingested "
        f"{result.chunks_indexed} chunks from {result.files_indexed} files "
        f"into '{result.collection}'."
    )


if __name__ == "__main__":
    main()
