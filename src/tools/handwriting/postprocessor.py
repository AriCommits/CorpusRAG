"""Post-processing of OCR output: metadata attachment, deduplication, content hashing."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from src.tools.handwriting.walker import DiscoveredImage


@dataclass
class ProcessedPage:
    """A handwritten page after OCR and correction."""

    content: str  # Corrected markdown
    source_image: str  # Original image path
    relative_path: str  # Relative to scan root
    folder_hierarchy: list[str]  # Folder path parts
    file_hash: str  # SHA-256 of source image
    content_hash: str  # SHA-256 of OCR content (first 16 hex chars)
    correction_confidence: float  # 0.0-1.0, lower = more corrections made
    is_blank: bool  # True if content is [BLANK_PAGE]
    user_tags: list[str] = field(default_factory=list)  # Tags injected from user


def build_page(
    image: DiscoveredImage,
    corrected_text: str,
    correction_confidence: float,
    user_tags: list[str] | None = None,
) -> ProcessedPage:
    """
    Build a ProcessedPage from a DiscoveredImage and corrected text.

    Args:
        image: DiscoveredImage from walker.
        corrected_text: Corrected markdown text.
        correction_confidence: Confidence score (0.0-1.0).
        user_tags: Optional tags to attach to the page.

    Returns:
        ProcessedPage instance.
    """
    # Content hash: first 16 hex chars of sha256
    content_hash = hashlib.sha256(corrected_text.encode()).hexdigest()[:16]

    # is_blank: check if content is exactly "[BLANK_PAGE]" after stripping
    is_blank = corrected_text.strip() == "[BLANK_PAGE]"

    # user_tags defaults to empty list when None
    tags = user_tags or []

    return ProcessedPage(
        content=corrected_text,
        source_image=str(image.path),
        relative_path=image.relative_path,
        folder_hierarchy=image.folder_hierarchy,
        file_hash=image.file_hash,
        content_hash=content_hash,
        correction_confidence=correction_confidence,
        is_blank=is_blank,
        user_tags=tags,
    )


def build_chromadb_metadata(page: ProcessedPage) -> dict:
    """
    Build ChromaDB metadata dict for a processed page.

    Produces flat keys for ChromaDB's scalar-based filtering:
    - folder_depth_0, folder_depth_1, folder_depth_2 (empty string if missing)
    - tag_prefixes: unique first parts of tags containing "/"

    Args:
        page: ProcessedPage instance.

    Returns:
        Dictionary with 13 fields (parent_id added by chunker).
    """
    # Extract folder depths with defaults to empty string
    folder_depth_0 = page.folder_hierarchy[0] if len(page.folder_hierarchy) > 0 else ""
    folder_depth_1 = page.folder_hierarchy[1] if len(page.folder_hierarchy) > 1 else ""
    folder_depth_2 = page.folder_hierarchy[2] if len(page.folder_hierarchy) > 2 else ""

    # Extract tag prefixes from tags containing "/"
    tag_prefixes = list({t.split("/")[0] for t in page.user_tags if "/" in t})

    return {
        "source_file": page.source_image,
        "source_type": "handwriting",
        "relative_path": page.relative_path,
        "folder_hierarchy": page.folder_hierarchy,
        "folder_depth_0": folder_depth_0,
        "folder_depth_1": folder_depth_1,
        "folder_depth_2": folder_depth_2,
        "file_hash": page.file_hash,
        "content_hash": page.content_hash,
        "correction_confidence": page.correction_confidence,
        "tags": page.user_tags,
        "tag_prefixes": tag_prefixes,
    }
