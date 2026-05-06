"""Tests for the postprocessor module."""

import hashlib
from pathlib import Path

import pytest

from src.tools.handwriting.postprocessor import (
    ProcessedPage,
    build_chromadb_metadata,
    build_page,
)
from src.tools.handwriting.walker import DiscoveredImage


@pytest.fixture
def sample_discovered_image():
    """Create a sample DiscoveredImage for testing."""
    return DiscoveredImage(
        path=Path("/scans/2020/january/page_001.jpg"),
        relative_path="2020/january/page_001.jpg",
        folder_hierarchy=["2020", "january"],
        file_hash="a1b2c3d4e5f6g7h8",
        file_size_bytes=15000,
    )


def test_processed_page_dataclass():
    """Test ProcessedPage dataclass creation."""
    page = ProcessedPage(
        content="Some OCR text",
        source_image="/scans/2020/january/page_001.jpg",
        relative_path="2020/january/page_001.jpg",
        folder_hierarchy=["2020", "january"],
        file_hash="a1b2c3d4e5f6g7h8",
        content_hash="1a2b3c4d5e6f7g8h",
        correction_confidence=0.85,
        is_blank=False,
        user_tags=["Year/2020", "Domain/Engineering"],
    )

    assert page.content == "Some OCR text"
    assert page.source_image == "/scans/2020/january/page_001.jpg"
    assert page.relative_path == "2020/january/page_001.jpg"
    assert page.folder_hierarchy == ["2020", "january"]
    assert page.file_hash == "a1b2c3d4e5f6g7h8"
    assert page.content_hash == "1a2b3c4d5e6f7g8h"
    assert page.correction_confidence == 0.85
    assert page.is_blank is False
    assert page.user_tags == ["Year/2020", "Domain/Engineering"]


def test_processed_page_user_tags_default():
    """Test that user_tags defaults to empty list."""
    page = ProcessedPage(
        content="Text",
        source_image="/path/img.jpg",
        relative_path="img.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        content_hash="content_hash",
        correction_confidence=0.9,
        is_blank=False,
    )

    assert page.user_tags == []


def test_build_page_basic(sample_discovered_image):
    """Test build_page with basic inputs."""
    corrected_text = "# Lecture Notes\n\nThis is a test."
    confidence = 0.88

    page = build_page(sample_discovered_image, corrected_text, confidence)

    assert page.content == corrected_text
    assert page.source_image == str(sample_discovered_image.path)
    assert page.relative_path == sample_discovered_image.relative_path
    assert page.folder_hierarchy == sample_discovered_image.folder_hierarchy
    assert page.file_hash == sample_discovered_image.file_hash
    assert page.correction_confidence == confidence
    assert page.is_blank is False
    assert page.user_tags == []


def test_build_page_with_tags(sample_discovered_image):
    """Test build_page with user tags."""
    corrected_text = "Some content"
    confidence = 0.9
    tags = ["Year/2020", "Project/Circuit"]

    page = build_page(sample_discovered_image, corrected_text, confidence, tags)

    assert page.user_tags == tags


def test_build_page_with_none_tags(sample_discovered_image):
    """Test build_page with None tags defaults to empty list."""
    corrected_text = "Some content"
    confidence = 0.9

    page = build_page(sample_discovered_image, corrected_text, confidence, None)

    assert page.user_tags == []


def test_build_page_content_hash_determinism(sample_discovered_image):
    """Test that content_hash is deterministic."""
    corrected_text = "Same content"
    confidence = 0.9

    page1 = build_page(sample_discovered_image, corrected_text, confidence)
    page2 = build_page(sample_discovered_image, corrected_text, confidence)

    assert page1.content_hash == page2.content_hash


def test_build_page_content_hash_first_16_chars(sample_discovered_image):
    """Test that content_hash is first 16 hex characters of SHA256."""
    corrected_text = "Test content"
    full_hash = hashlib.sha256(corrected_text.encode()).hexdigest()
    expected_hash = full_hash[:16]

    page = build_page(sample_discovered_image, corrected_text, 0.9)

    assert page.content_hash == expected_hash
    assert len(page.content_hash) == 16


def test_build_page_content_hash_different_for_different_text(sample_discovered_image):
    """Test that different text produces different hashes."""
    page1 = build_page(sample_discovered_image, "Text A", 0.9)
    page2 = build_page(sample_discovered_image, "Text B", 0.9)

    assert page1.content_hash != page2.content_hash


def test_build_page_is_blank_true(sample_discovered_image):
    """Test is_blank detection for [BLANK_PAGE] content."""
    page = build_page(sample_discovered_image, "[BLANK_PAGE]", 0.5)
    assert page.is_blank is True

    page = build_page(sample_discovered_image, "  [BLANK_PAGE]  ", 0.5)
    assert page.is_blank is True


def test_build_page_is_blank_false(sample_discovered_image):
    """Test is_blank is False for non-blank content."""
    page = build_page(sample_discovered_image, "Some text", 0.9)
    assert page.is_blank is False

    page = build_page(sample_discovered_image, "[BLANK_PAGE] followed by text", 0.9)
    assert page.is_blank is False


def test_build_page_is_blank_empty_string(sample_discovered_image):
    """Test is_blank with empty string."""
    page = build_page(sample_discovered_image, "", 0.5)
    assert page.is_blank is False


def test_build_chromadb_metadata_all_fields(sample_discovered_image):
    """Test that build_chromadb_metadata includes all required fields."""
    page = build_page(sample_discovered_image, "Test content", 0.85, ["Year/2020"])
    metadata = build_chromadb_metadata(page)

    # Check all 12 fields are present (parent_id added by chunker)
    required_fields = {
        "source_file",
        "source_type",
        "relative_path",
        "folder_hierarchy",
        "folder_depth_0",
        "folder_depth_1",
        "folder_depth_2",
        "file_hash",
        "content_hash",
        "correction_confidence",
        "tags",
        "tag_prefixes",
    }
    assert set(metadata.keys()) == required_fields


def test_build_chromadb_metadata_values(sample_discovered_image):
    """Test correct values in chromadb metadata."""
    page = build_page(sample_discovered_image, "Test content", 0.75, ["Year/2020"])
    metadata = build_chromadb_metadata(page)

    assert metadata["source_file"] == str(sample_discovered_image.path)
    assert metadata["source_type"] == "handwriting"
    assert metadata["relative_path"] == "2020/january/page_001.jpg"
    assert metadata["folder_hierarchy"] == ["2020", "january"]
    assert metadata["folder_depth_0"] == "2020"
    assert metadata["folder_depth_1"] == "january"
    assert metadata["folder_depth_2"] == ""
    assert metadata["file_hash"] == sample_discovered_image.file_hash
    assert metadata["correction_confidence"] == 0.75
    assert metadata["tags"] == ["Year/2020"]


def test_build_chromadb_metadata_folder_depths_deep_hierarchy():
    """Test folder_depth fields with deep hierarchy."""
    image = DiscoveredImage(
        path=Path("/scans/2021/projects/circuit/design/page.jpg"),
        relative_path="2021/projects/circuit/design/page.jpg",
        folder_hierarchy=["2021", "projects", "circuit", "design"],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9)
    metadata = build_chromadb_metadata(page)

    assert metadata["folder_depth_0"] == "2021"
    assert metadata["folder_depth_1"] == "projects"
    assert metadata["folder_depth_2"] == "circuit"
    # Note: only depth 0, 1, 2 are included, not deeper levels


def test_build_chromadb_metadata_folder_depths_shallow_hierarchy():
    """Test folder_depth fields with shallow hierarchy."""
    image = DiscoveredImage(
        path=Path("/scans/2020/page.jpg"),
        relative_path="2020/page.jpg",
        folder_hierarchy=["2020"],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9)
    metadata = build_chromadb_metadata(page)

    assert metadata["folder_depth_0"] == "2020"
    assert metadata["folder_depth_1"] == ""
    assert metadata["folder_depth_2"] == ""


def test_build_chromadb_metadata_folder_depths_root_level():
    """Test folder_depth fields with root-level file."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9)
    metadata = build_chromadb_metadata(page)

    assert metadata["folder_depth_0"] == ""
    assert metadata["folder_depth_1"] == ""
    assert metadata["folder_depth_2"] == ""


def test_build_chromadb_metadata_tag_prefixes_with_slash():
    """Test tag_prefixes extraction from tags with '/'."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9, ["Year/2020", "Domain/Engineering"])
    metadata = build_chromadb_metadata(page)

    assert set(metadata["tag_prefixes"]) == {"Year", "Domain"}


def test_build_chromadb_metadata_tag_prefixes_no_slash():
    """Test tag_prefixes extraction ignores tags without '/'."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9, ["plain_tag", "another_tag"])
    metadata = build_chromadb_metadata(page)

    assert metadata["tag_prefixes"] == []


def test_build_chromadb_metadata_tag_prefixes_mixed():
    """Test tag_prefixes with mix of slash and non-slash tags."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(
        image,
        "Content",
        0.9,
        ["Year/2020", "plain", "Domain/Engineering", "another_plain"],
    )
    metadata = build_chromadb_metadata(page)

    assert set(metadata["tag_prefixes"]) == {"Year", "Domain"}


def test_build_chromadb_metadata_tag_prefixes_unique():
    """Test that tag_prefixes are unique (no duplicates)."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(
        image,
        "Content",
        0.9,
        ["Year/2020", "Year/2021", "Domain/Engineering"],
    )
    metadata = build_chromadb_metadata(page)

    # Should have 2 unique prefixes: Year and Domain
    assert len(metadata["tag_prefixes"]) == 2
    assert set(metadata["tag_prefixes"]) == {"Year", "Domain"}


def test_build_chromadb_metadata_empty_tags():
    """Test metadata when page has no tags."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9, [])
    metadata = build_chromadb_metadata(page)

    assert metadata["tags"] == []
    assert metadata["tag_prefixes"] == []


def test_build_chromadb_metadata_confidence_score():
    """Test that correction_confidence is preserved in metadata."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.42)
    metadata = build_chromadb_metadata(page)

    assert metadata["correction_confidence"] == 0.42
    assert isinstance(metadata["correction_confidence"], float)


def test_build_page_with_empty_folder_hierarchy(sample_discovered_image):
    """Test build_page with root-level image (no folders)."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=[],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9)

    assert page.folder_hierarchy == []
    assert page.relative_path == "page.jpg"


def test_build_chromadb_metadata_source_type_always_handwriting():
    """Test that source_type is always 'handwriting'."""
    image = DiscoveredImage(
        path=Path("/scans/page.jpg"),
        relative_path="page.jpg",
        folder_hierarchy=["2020"],
        file_hash="hash",
        file_size_bytes=1000,
    )

    page = build_page(image, "Content", 0.9)
    metadata = build_chromadb_metadata(page)

    assert metadata["source_type"] == "handwriting"
