"""Document ingestion for CorpusCallosum."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .chroma import create_chroma_client
from .config import Config, get_config
from .embeddings import EmbeddingBackend, create_embedding_backend

if TYPE_CHECKING:
    pass

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
        embedding_backend: EmbeddingBackend | None = None,
    ) -> None:
        self.config = config or get_config()
        self.client = chroma_client or create_chroma_client(self.config)
        self._embedding_backend = embedding_backend

    @property
    def embedding_backend(self) -> EmbeddingBackend:
        if self._embedding_backend is None:
            self._embedding_backend = create_embedding_backend(self.config)
        return self._embedding_backend

    def ingest_path(self, path: str | Path, collection_name: str) -> IngestResult:
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Path does not exist: {source}")
        if not collection_name.strip():
            raise ValueError("collection_name cannot be empty")

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
        embeddings = self.embedding_backend.encode(documents)

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
    parser = argparse.ArgumentParser(
        prog="corpus-ingest",
        description="Ingest documents into ChromaDB",
    )
    parser.add_argument(
        "-p",
        "--path",
        required=True,
        help="File or directory to ingest",
    )
    parser.add_argument(
        "-c",
        "--collection",
        required=True,
        help="Target collection name",
    )
    parser.add_argument(
        "--convert",
        action="store_true",
        help="Convert unsupported files to markdown before ingesting",
    )
    return parser


def _scan_unsupported_files(path: Path) -> dict[str, list[Path]]:
    """Scan directory for files that cannot be directly ingested."""
    unsupported: dict[str, list[Path]] = defaultdict(list)

    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            unsupported[path.suffix.lower()].append(path)
        return dict(unsupported)

    for file_path in path.rglob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext and ext not in SUPPORTED_EXTENSIONS:
                unsupported[ext].append(file_path)

    return dict(unsupported)


def _warn_unsupported_files(path: Path, unsupported: dict[str, list[Path]]) -> None:
    """Print warning about unsupported files and suggest conversion."""
    # Only warn about convertible formats
    from .convert import FileConverter

    converter = FileConverter()
    convertible_exts = converter.get_supported_extensions()

    convertible_found: dict[str, int] = {}
    for ext, files in unsupported.items():
        if ext in convertible_exts:
            convertible_found[ext] = len(files)

    if not convertible_found:
        return

    total = sum(convertible_found.values())
    ext_list = ", ".join(f"{count} {ext}" for ext, count in sorted(convertible_found.items()))

    print(f"\nWarning: Found {total} file(s) that cannot be directly ingested: {ext_list}")
    print("These files can be converted to markdown first.")
    print("\nTo convert and then ingest, run:")
    print(f"  corpus-convert {path}")
    print(f"  corpus-ingest --path {path}/corpus_converted --collection <collection_name>")
    print("\nOr use the --convert flag to do both automatically:")
    print(f"  corpus-ingest --path {path} --collection <collection_name> --convert\n")


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    source_path = Path(args.path).expanduser().resolve()

    if not source_path.exists():
        print(f"Error: Path does not exist: {source_path}", file=sys.stderr)
        sys.exit(1)

    # Check for unsupported files
    unsupported = _scan_unsupported_files(source_path)

    if args.convert and unsupported:
        # Convert files first
        from .convert import DEFAULT_OUTPUT_DIR, FileConverter

        print("Converting unsupported files to markdown...")
        converter = FileConverter()
        results = converter.convert_directory(source_path)

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        if success_count > 0:
            print(f"Converted {success_count} file(s) to markdown.")
        if fail_count > 0:
            print(f"Failed to convert {fail_count} file(s).")

        # Update source path to the converted directory
        converted_path = source_path / DEFAULT_OUTPUT_DIR
        if converted_path.exists():
            source_path = converted_path
            print(f"Ingesting from: {source_path}\n")
    elif unsupported:
        # Warn about unsupported files
        _warn_unsupported_files(source_path, unsupported)

    ingester = Ingester()
    result = ingester.ingest_path(path=source_path, collection_name=args.collection)
    print(
        "Ingested "
        f"{result.chunks_indexed} chunks from {result.files_indexed} files "
        f"into '{result.collection}'."
    )


if __name__ == "__main__":
    main()
