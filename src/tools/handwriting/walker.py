"""Recursive directory walker for discovering images to be ingested."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

# Supported image extensions (case-insensitive matching)
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}


@dataclass
class DiscoveredImage:
    """Metadata for a discovered image file."""

    path: Path
    relative_path: str  # Relative to the root scan directory
    folder_hierarchy: list[str]  # e.g. ["2020", "january"]
    file_hash: str  # SHA-256 of file contents for dedup
    file_size_bytes: int


def walk_directory(
    root: Path,
    recursive: bool = True,
    extensions: set[str] = SUPPORTED_EXTENSIONS,
    max_depth: int | None = None,
) -> list[DiscoveredImage]:
    """
    Walk a directory and return all image files.

    Args:
        root: Root directory to scan.
        recursive: If True, descend into subdirectories.
                   If False, only process top-level files.
        extensions: Set of file extensions to include.
        max_depth: Maximum directory depth to traverse.
                   0 = root only, 1 = root + 1 level, None = unlimited.

    Returns:
        List of DiscoveredImage, sorted by path for consistent ordering.
    """
    root = Path(root)
    pattern = "**/*" if recursive else "*"
    all_files = [
        p for p in root.glob(pattern)
        if p.is_file() and p.suffix.lower() in extensions
    ]

    # Filter by max_depth if specified
    if recursive and max_depth is not None:
        filtered_files = []
        for p in all_files:
            try:
                relative = p.relative_to(root)
                # Depth is number of parts minus 1 (the filename is part of the path)
                depth = len(relative.parts) - 1
                if depth <= max_depth:
                    filtered_files.append(p)
            except ValueError:
                # Path is not relative to root, skip it
                pass
        all_files = filtered_files

    all_files.sort()

    results = []
    for path in all_files:
        relative = path.relative_to(root)
        hierarchy = list(relative.parts[:-1])  # folders only, not filename
        file_hash = _hash_file(path)
        # Normalize relative_path to use forward slashes for cross-platform consistency
        relative_path_str = str(relative).replace("\\", "/")
        results.append(
            DiscoveredImage(
                path=path,
                relative_path=relative_path_str,
                folder_hierarchy=hierarchy,
                file_hash=file_hash,
                file_size_bytes=path.stat().st_size,
            )
        )

    return results


def _hash_file(path: Path) -> str:
    """
    SHA-256 hash of file contents for deduplication.

    Reads file in 64 KiB chunks to avoid loading entire file into memory.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)  # 64 KiB
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def filter_already_ingested(
    images: list[DiscoveredImage],
    ingested_hashes: set[str],
) -> tuple[list[DiscoveredImage], int]:
    """
    Remove images already present in ChromaDB by hash.

    Args:
        images: List of discovered images.
        ingested_hashes: Set of SHA-256 hashes already in the database.

    Returns:
        Tuple of (new_images, skipped_count).
    """
    new = [img for img in images if img.file_hash not in ingested_hashes]
    skipped = len(images) - len(new)
    return new, skipped
