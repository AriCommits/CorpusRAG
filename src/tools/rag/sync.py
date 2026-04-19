from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from db import DatabaseBackend
from tools.rag.config import RAGConfig
from tools.rag.ingest import RAGIngester


@dataclass(frozen=True)
class SyncResult:
    collection: str
    new_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]
    unchanged_files: list[str]
    chunks_added: int
    chunks_removed: int


class RAGSyncer:
    """Synchronize a directory with a RAG collection, detecting changes."""

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        self.config = config
        self.db = db
        self.ingester = RAGIngester(config, db)

    def sync(self, path: Path | str, collection: str, dry_run: bool = False) -> SyncResult:
        """Sync a directory with the RAG collection."""
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Path does not exist: {source}")

        full_collection = f"{self.config.collection_prefix}_{collection}"

        # 1. Enumerate files on disk
        disk_files = list(self.ingester._iter_source_files(source))

        disk_file_hashes = {}
        for file_path in disk_files:
            relative_path = (
                str(file_path.relative_to(source)) if file_path != source else file_path.name
            )
            content = self.ingester._read_file(file_path)
            file_hash = sha256(content.encode("utf-8")).hexdigest()
            disk_file_hashes[relative_path] = (file_path, file_hash)

        # 3. Query the DB for existing files
        # We'll get all unique source_file and file_hash pairs.
        db_files = {}
        if self.db.collection_exists(full_collection):
            # Hack: query a large limit to get all metadata
            # Or use a get with include=["metadatas"]
            try:
                # In chromadb backend, get_collection returns the raw collection
                col = self.db.get_collection(full_collection)
                results = col.get(include=["metadatas"])
                if results and "metadatas" in results and results["metadatas"]:
                    for meta in results["metadatas"]:
                        if meta:
                            sf = meta.get("source_file")
                            fh = meta.get("file_hash")
                            if sf and fh:
                                db_files[sf] = fh
            except Exception:
                pass

        new_files = []
        modified_files = []
        unchanged_files = []
        deleted_files = []

        # 4. Compare
        for rel_path, (file_path, file_hash) in disk_file_hashes.items():
            if rel_path not in db_files:
                new_files.append(rel_path)
            elif db_files[rel_path] != file_hash:
                modified_files.append(rel_path)
            else:
                unchanged_files.append(rel_path)

        for rel_path in db_files:
            if rel_path not in disk_file_hashes:
                deleted_files.append(rel_path)

        chunks_added = 0
        chunks_removed = 0

        # 5. Apply changes if not dry_run
        if not dry_run:
            # Process deleted
            for rel_path in deleted_files:
                if self.db.collection_exists(full_collection):
                    try:
                        # Find chunks to remove to count them
                        metadatas = self.db.get_metadata_by_filter(
                            full_collection, where={"source_file": rel_path}
                        )
                        chunks_removed += len(metadatas) if metadatas else 0
                        self.db.delete_by_metadata(full_collection, where={"source_file": rel_path})
                    except Exception:
                        pass
                try:
                    self.ingester.parent_store.delete_by_metadata(
                        lambda m: m.get("source_file") == rel_path
                    )
                except Exception:
                    pass

            # Process modified (delete old, then ingest new)
            for rel_path in modified_files:
                if self.db.collection_exists(full_collection):
                    try:
                        metadatas = self.db.get_metadata_by_filter(
                            full_collection, where={"source_file": rel_path}
                        )
                        chunks_removed += len(metadatas) if metadatas else 0
                        self.db.delete_by_metadata(full_collection, where={"source_file": rel_path})
                    except Exception:
                        pass
                try:
                    self.ingester.parent_store.delete_by_metadata(
                        lambda m: m.get("source_file") == rel_path
                    )
                except Exception:
                    pass
                file_path, _ = disk_file_hashes[rel_path]
                res = self.ingester.ingest_path(file_path, collection)
                chunks_added += res.chunks_indexed

            # Process new
            for rel_path in new_files:
                file_path, _ = disk_file_hashes[rel_path]
                res = self.ingester.ingest_path(file_path, collection)
                chunks_added += res.chunks_indexed

        return SyncResult(
            collection=collection,
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            unchanged_files=unchanged_files,
            chunks_added=chunks_added,
            chunks_removed=chunks_removed,
        )
