"""Tests for the chunker module."""

from pathlib import Path

import pytest

from src.tools.handwriting.chunker import (
    HandwritingChildChunk,
    build_child_chunks,
)
from src.tools.handwriting.postprocessor import (
    ProcessedPage,
    build_chromadb_metadata,
    build_page,
)
from src.tools.handwriting.walker import DiscoveredImage


@pytest.fixture
def sample_pages():
    """Create sample ProcessedPage instances for testing."""
    pages = []
    for i in range(5):
        image = DiscoveredImage(
            path=Path(f"/scans/2020/january/page_{i:03d}.jpg"),
            relative_path=f"2020/january/page_{i:03d}.jpg",
            folder_hierarchy=["2020", "january"],
            file_hash=f"hash_{i}",
            file_size_bytes=5000,
        )
        page = build_page(image, f"Content of page {i}", 0.85)
        pages.append(page)
    return pages


@pytest.fixture
def sample_pages_with_blanks():
    """Create sample ProcessedPage instances with some blank pages."""
    pages = []
    contents = [
        "Content of page 0",
        "[BLANK_PAGE]",  # Blank at index 1
        "Content of page 2",
        "[BLANK_PAGE]",  # Blank at index 3
        "Content of page 4",
    ]
    for i, content in enumerate(contents):
        image = DiscoveredImage(
            path=Path(f"/scans/2020/january/page_{i:03d}.jpg"),
            relative_path=f"2020/january/page_{i:03d}.jpg",
            folder_hierarchy=["2020", "january"],
            file_hash=f"hash_{i}",
            file_size_bytes=5000,
        )
        page = build_page(image, content, 0.85)
        pages.append(page)
    return pages


def test_handwriting_child_chunk_dataclass():
    """Test HandwritingChildChunk dataclass creation."""
    metadata = {"source_file": "test.jpg", "parent_id": "parent_1"}
    chunk = HandwritingChildChunk(
        content="Test content",
        parent_id="parent_1",
        metadata=metadata,
    )

    assert chunk.content == "Test content"
    assert chunk.parent_id == "parent_1"
    assert chunk.metadata == metadata


def test_build_child_chunks_basic(sample_pages):
    """Test build_child_chunks with default context_window."""
    chunks = build_child_chunks(sample_pages, "parent_1")

    # With 5 non-blank pages and context_window=1, should get 5 chunks
    assert len(chunks) == 5
    assert all(isinstance(c, HandwritingChildChunk) for c in chunks)


def test_build_child_chunks_context_window_zero(sample_pages):
    """Test build_child_chunks with context_window=0 produces single-page chunks."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=0)

    assert len(chunks) == 5
    # Each chunk should contain only one page's content
    assert chunks[0].content == "Content of page 0"
    assert chunks[1].content == "Content of page 1"
    assert chunks[2].content == "Content of page 2"


def test_build_child_chunks_context_window_one(sample_pages):
    """Test build_child_chunks with context_window=1 includes adjacent pages."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=1)

    assert len(chunks) == 5

    # First page: should include page 0 and 1
    assert "Content of page 0" in chunks[0].content
    assert "Content of page 1" in chunks[0].content
    assert "Content of page 2" not in chunks[0].content

    # Middle page: should include pages 1, 2, 3
    assert "Content of page 1" in chunks[2].content
    assert "Content of page 2" in chunks[2].content
    assert "Content of page 3" in chunks[2].content

    # Last page: should include pages 3 and 4
    assert "Content of page 3" in chunks[4].content
    assert "Content of page 4" in chunks[4].content
    assert "Content of page 2" not in chunks[4].content


def test_build_child_chunks_joiner(sample_pages):
    """Test that chunks use correct joiner between pages."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=1)

    # Check that joiner is present between pages
    assert "\n\n---\n\n" in chunks[1].content


def test_build_child_chunks_blank_pages_skipped(sample_pages_with_blanks):
    """Test that blank pages are skipped entirely (no chunk emitted)."""
    chunks = build_child_chunks(sample_pages_with_blanks, "parent_1", context_window=0)

    # Should only get 3 chunks (pages 0, 2, 4), not 5
    assert len(chunks) == 3
    assert chunks[0].content == "Content of page 0"
    assert chunks[1].content == "Content of page 2"
    assert chunks[2].content == "Content of page 4"


def test_build_child_chunks_blank_pages_excluded_from_window(
    sample_pages_with_blanks,
):
    """Test that blank pages are excluded from context window."""
    chunks = build_child_chunks(sample_pages_with_blanks, "parent_1", context_window=1)

    # Should have 3 chunks (one for each non-blank page)
    assert len(chunks) == 3

    # First chunk (page 0): window is [-1:2], but filtered gives [0, 2] (not blank 1)
    # But actually page 0 with window 1 should be [0:2], filtered to just [0, 2]
    # Actually let me recalculate: page 0 is at index 0, window 1 means [max(0,0-1):min(5,0+1+1)]
    # = [0:2], which contains pages[0:2] = [page0, blank1]
    # After filtering blanks: [page0] only
    assert chunks[0].content == "Content of page 0"

    # Middle chunk (page 2): window is [1:4]
    # pages[1:4] = [blank1, page2, blank3]
    # After filtering blanks: [page2] only
    assert chunks[1].content == "Content of page 2"

    # Last chunk (page 4): window is [3:5]
    # pages[3:5] = [blank3, page4]
    # After filtering blanks: [page4] only
    assert chunks[2].content == "Content of page 4"


def test_build_child_chunks_parent_id_propagated(sample_pages):
    """Test that parent_id is correctly set on all chunks."""
    parent_id = "parent_folder_key"
    chunks = build_child_chunks(sample_pages, parent_id, context_window=0)

    for chunk in chunks:
        assert chunk.parent_id == parent_id
        assert chunk.metadata["parent_id"] == parent_id


def test_build_child_chunks_metadata_from_anchor_page(sample_pages):
    """Test that metadata refers to anchor page, not context pages."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=1)

    # For chunk at index 2 (anchor page 2):
    # Content should include pages 1, 2, 3
    # But metadata should be from page 2 (the anchor)
    metadata = chunks[2].metadata
    assert metadata["content_hash"] == sample_pages[2].content_hash
    assert "page 2" in chunks[2].content  # Content includes page 2


def test_build_child_chunks_metadata_has_all_fields(sample_pages):
    """Test that each chunk's metadata has all required fields."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=0)

    for chunk in chunks:
        # Should have all fields from build_chromadb_metadata plus parent_id
        assert "source_file" in chunk.metadata
        assert "source_type" in chunk.metadata
        assert "relative_path" in chunk.metadata
        assert "folder_hierarchy" in chunk.metadata
        assert "folder_depth_0" in chunk.metadata
        assert "folder_depth_1" in chunk.metadata
        assert "folder_depth_2" in chunk.metadata
        assert "file_hash" in chunk.metadata
        assert "content_hash" in chunk.metadata
        assert "correction_confidence" in chunk.metadata
        assert "tags" in chunk.metadata
        assert "tag_prefixes" in chunk.metadata
        assert "parent_id" in chunk.metadata


def test_build_child_chunks_empty_pages_list():
    """Test build_child_chunks with empty pages list."""
    chunks = build_child_chunks([], "parent_1", context_window=1)
    assert chunks == []


def test_build_child_chunks_all_blank_pages():
    """Test build_child_chunks when all pages are blank."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )
    pages = [build_page(image, "[BLANK_PAGE]", 0.5) for _ in range(3)]

    chunks = build_child_chunks(pages, "parent_1", context_window=1)

    # No non-blank pages, so no chunks
    assert chunks == []


def test_build_child_chunks_single_non_blank_page(sample_pages_with_blanks):
    """Test build_child_chunks when only one page is non-blank."""
    # Create pages where only one is non-blank
    pages = [
        build_page(
            DiscoveredImage(
                path=Path("/scans/page_0.jpg"),
                relative_path="page_0.jpg",
                folder_hierarchy=[],
                file_hash="h0",
                file_size_bytes=1000,
            ),
            "[BLANK_PAGE]",
            0.5,
        ),
        build_page(
            DiscoveredImage(
                path=Path("/scans/page_1.jpg"),
                relative_path="page_1.jpg",
                folder_hierarchy=[],
                file_hash="h1",
                file_size_bytes=1000,
            ),
            "Only content",
            0.9,
        ),
        build_page(
            DiscoveredImage(
                path=Path("/scans/page_2.jpg"),
                relative_path="page_2.jpg",
                folder_hierarchy=[],
                file_hash="h2",
                file_size_bytes=1000,
            ),
            "[BLANK_PAGE]",
            0.5,
        ),
    ]

    chunks = build_child_chunks(pages, "parent_1", context_window=1)

    assert len(chunks) == 1
    assert chunks[0].content == "Only content"


def test_build_child_chunks_context_window_larger_than_pages(sample_pages):
    """Test context_window larger than the number of pages."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=10)

    # All chunks should include all pages
    assert len(chunks) == 5
    for chunk in chunks:
        assert "Content of page 0" in chunk.content
        assert "Content of page 4" in chunk.content


def test_build_child_chunks_context_window_two(sample_pages):
    """Test with context_window=2."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=2)

    # First chunk (index 0): window [0:3], includes pages 0, 1, 2
    assert "Content of page 0" in chunks[0].content
    assert "Content of page 1" in chunks[0].content
    assert "Content of page 2" in chunks[0].content
    assert "Content of page 3" not in chunks[0].content

    # Middle chunk (index 2): window [0:5], includes all pages
    assert "Content of page 0" in chunks[2].content
    assert "Content of page 4" in chunks[2].content


def test_build_child_chunks_metadata_source_file_correct(sample_pages):
    """Test that metadata source_file refers to anchor page."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=1)

    # Chunk at index 1 should have source_file pointing to page 1
    expected_path = str(sample_pages[1].source_image)
    assert chunks[1].metadata["source_file"] == expected_path


def test_build_child_chunks_metadata_content_hash_from_anchor(sample_pages):
    """Test that metadata content_hash is from anchor page."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=1)

    # Chunk metadata content_hash should match the anchor page's hash
    for i, chunk in enumerate(chunks):
        assert chunk.metadata["content_hash"] == sample_pages[i].content_hash


def test_build_child_chunks_joiner_format(sample_pages):
    """Test the exact format of the joiner between pages."""
    chunks = build_child_chunks(sample_pages, "parent_1", context_window=1)

    # Check exact joiner format
    joiner = "\n\n---\n\n"
    for chunk in chunks:
        # If chunk has multiple pages, it should contain the joiner
        if "Content of page" in chunk.content and chunk.content.count("Content of page") > 1:
            assert joiner in chunk.content


def test_build_child_chunks_with_tags_in_metadata(sample_pages):
    """Test that user tags are preserved in metadata."""
    # Create pages with tags
    pages_with_tags = []
    for i, page in enumerate(sample_pages):
        page_copy = ProcessedPage(
            content=page.content,
            source_image=page.source_image,
            relative_path=page.relative_path,
            folder_hierarchy=page.folder_hierarchy,
            file_hash=page.file_hash,
            content_hash=page.content_hash,
            correction_confidence=page.correction_confidence,
            is_blank=page.is_blank,
            user_tags=["Year/2020", "Domain/Engineering"] if i % 2 == 0 else [],
        )
        pages_with_tags.append(page_copy)

    chunks = build_child_chunks(pages_with_tags, "parent_1", context_window=0)

    # Check tags are in metadata
    assert chunks[0].metadata["tags"] == ["Year/2020", "Domain/Engineering"]
    assert chunks[1].metadata["tags"] == []
    assert chunks[2].metadata["tags"] == ["Year/2020", "Domain/Engineering"]


def test_build_child_chunks_blank_at_boundaries(sample_pages_with_blanks):
    """Test context window handling when blanks are at window boundaries."""
    # Pages: [content, blank, content, blank, content]
    chunks = build_child_chunks(sample_pages_with_blanks, "parent_1", context_window=1)

    # Page 2 (index 2) with window 1: [1:4] = [blank, content, blank] → filtered to [content]
    assert chunks[1].content == "Content of page 2"


def test_build_child_chunks_maintains_order():
    """Test that chunks are emitted in page order."""
    pages = []
    contents = [f"Page {i}" for i in range(5)]
    for i, content in enumerate(contents):
        image = DiscoveredImage(
            path=Path(f"/scans/page_{i}.jpg"),
            relative_path=f"page_{i}.jpg",
            folder_hierarchy=[],
            file_hash=f"h{i}",
            file_size_bytes=1000,
        )
        page = build_page(image, content, 0.9)
        pages.append(page)

    chunks = build_child_chunks(pages, "parent_1", context_window=0)

    # Chunks should maintain the original page order
    for i, chunk in enumerate(chunks):
        assert f"Page {i}" in chunk.content
