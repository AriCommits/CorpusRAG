"""Tests for the directory walker module."""

import hashlib
from pathlib import Path

import pytest

from src.tools.handwriting.walker import (
    SUPPORTED_EXTENSIONS,
    DiscoveredImage,
    _hash_file,
    filter_already_ingested,
    walk_directory,
)


@pytest.fixture
def sample_images_dir(tmp_path):
    """Create a temporary directory with sample image files."""
    # Create directory structure
    (tmp_path / "2020" / "january").mkdir(parents=True, exist_ok=True)
    (tmp_path / "2020" / "february").mkdir(parents=True, exist_ok=True)
    (tmp_path / "2021" / "projects" / "circuit_design").mkdir(parents=True, exist_ok=True)
    (tmp_path / "root_level").mkdir(parents=True, exist_ok=True)

    # Create synthetic image files with different extensions
    files_to_create = [
        ("2020/january/page_001.jpg", b"fake jpg content 1"),
        ("2020/january/page_002.png", b"fake png content 2"),
        ("2020/february/page_001.jpg", b"fake jpg content for feb"),
        ("2021/projects/circuit_design/sketch_01.jpeg", b"fake jpeg sketch"),
        ("2021/projects/circuit_design/sketch_02.bmp", b"fake bmp content"),
        ("root_level/document.TIFF", b"fake tiff content"),
        ("root_level/photo.WebP", b"fake webp content"),
        ("root_level/unsupported.txt", b"should be ignored"),
        ("2020/readme.md", b"should be ignored"),
    ]

    for rel_path, content in files_to_create:
        file_path = tmp_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    return tmp_path


def test_discovered_image_dataclass():
    """Test DiscoveredImage dataclass creation."""
    path = Path("/some/path/image.jpg")
    img = DiscoveredImage(
        path=path,
        relative_path="2020/january/image.jpg",
        folder_hierarchy=["2020", "january"],
        file_hash="abc123",
        file_size_bytes=1024,
    )

    assert img.path == path
    assert img.relative_path == "2020/january/image.jpg"
    assert img.folder_hierarchy == ["2020", "january"]
    assert img.file_hash == "abc123"
    assert img.file_size_bytes == 1024


def test_walk_directory_recursive(sample_images_dir):
    """Test recursive directory walking."""
    images = walk_directory(sample_images_dir, recursive=True)

    # Should find 7 image files (excluding .txt and .md files)
    assert len(images) == 7

    # Verify paths are sorted
    paths = [img.relative_path for img in images]
    assert paths == sorted(paths)

    # Check that we have the expected files
    relative_paths = {img.relative_path for img in images}
    expected = {
        "2020/january/page_001.jpg",
        "2020/january/page_002.png",
        "2020/february/page_001.jpg",
        "2021/projects/circuit_design/sketch_01.jpeg",
        "2021/projects/circuit_design/sketch_02.bmp",
        "root_level/document.TIFF",
        "root_level/photo.WebP",
    }
    assert relative_paths == expected


def test_walk_directory_non_recursive(sample_images_dir):
    """Test non-recursive directory walking."""
    images = walk_directory(sample_images_dir, recursive=False)

    # With recursive=False, glob pattern is "*" which only matches top-level items
    # So we get no files (since all files are inside subdirectories)
    assert len(images) == 0
    assert images == []


def test_extension_filter_case_insensitive(sample_images_dir):
    """Test that extension filtering is case-insensitive."""
    images = walk_directory(sample_images_dir, recursive=True)

    # Both TIFF and WebP should be found despite being uppercase in filename
    relative_paths = {img.relative_path for img in images}
    assert "root_level/document.TIFF" in relative_paths
    assert "root_level/photo.WebP" in relative_paths


def test_extension_filter_excludes_unsupported(sample_images_dir):
    """Test that unsupported extensions are excluded."""
    images = walk_directory(sample_images_dir, recursive=True)

    relative_paths = {img.relative_path for img in images}
    # .txt and .md files should not be included
    assert "root_level/unsupported.txt" not in relative_paths
    assert "2020/readme.md" not in relative_paths


def test_folder_hierarchy_parsing(sample_images_dir):
    """Test that folder hierarchy is correctly extracted."""
    images = walk_directory(sample_images_dir, recursive=True)

    # Find the nested image
    img = next(img for img in images if "circuit_design" in img.relative_path)
    assert img.folder_hierarchy == ["2021", "projects", "circuit_design"]

    # Find a simpler image
    img = next(img for img in images if img.relative_path == "2020/january/page_001.jpg")
    assert img.folder_hierarchy == ["2020", "january"]

    # Find root level image
    img = next(img for img in images if img.relative_path == "root_level/document.TIFF")
    assert img.folder_hierarchy == ["root_level"]


def test_hash_file_determinism(sample_images_dir):
    """Test that _hash_file produces stable hashes across multiple runs."""
    test_file = sample_images_dir / "2020" / "january" / "page_001.jpg"

    hash1 = _hash_file(test_file)
    hash2 = _hash_file(test_file)
    hash3 = _hash_file(test_file)

    assert hash1 == hash2 == hash3
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hex digest is 64 chars


def test_hash_file_different_content(sample_images_dir):
    """Test that different files produce different hashes."""
    file1 = sample_images_dir / "2020" / "january" / "page_001.jpg"
    file2 = sample_images_dir / "2020" / "january" / "page_002.png"

    hash1 = _hash_file(file1)
    hash2 = _hash_file(file2)

    assert hash1 != hash2


def test_hash_file_chunked_reading(tmp_path):
    """Test that _hash_file reads in chunks correctly."""
    # Create a file larger than 64 KiB to test chunked reading
    large_file = tmp_path / "large.jpg"
    content = b"x" * (70000)  # 70 KB
    large_file.write_bytes(content)

    # Hash should match the expected SHA-256 of the content
    h = hashlib.sha256()
    h.update(content)
    expected_hash = h.hexdigest()

    actual_hash = _hash_file(large_file)
    assert actual_hash == expected_hash


def test_file_size_bytes(sample_images_dir):
    """Test that file_size_bytes is correctly recorded."""
    images = walk_directory(sample_images_dir, recursive=True)

    for img in images:
        assert img.file_size_bytes > 0
        assert img.file_size_bytes == img.path.stat().st_size


def test_filter_already_ingested_empty_ingested_set(sample_images_dir):
    """Test filtering when no images have been ingested."""
    images = walk_directory(sample_images_dir, recursive=True)
    new_images, skipped = filter_already_ingested(images, set())

    assert len(new_images) == len(images)
    assert skipped == 0


def test_filter_already_ingested_some_ingested(sample_images_dir):
    """Test filtering when some images are already ingested."""
    images = walk_directory(sample_images_dir, recursive=True)

    # Collect hashes of first 3 images as "already ingested"
    ingested_hashes = {images[0].file_hash, images[1].file_hash, images[2].file_hash}

    new_images, skipped = filter_already_ingested(images, ingested_hashes)

    assert len(new_images) == len(images) - 3
    assert skipped == 3
    assert all(img.file_hash not in ingested_hashes for img in new_images)


def test_filter_already_ingested_all_ingested(sample_images_dir):
    """Test filtering when all images have been ingested."""
    images = walk_directory(sample_images_dir, recursive=True)

    # Mark all images as ingested
    ingested_hashes = {img.file_hash for img in images}

    new_images, skipped = filter_already_ingested(images, ingested_hashes)

    assert len(new_images) == 0
    assert skipped == len(images)


def test_max_depth_none_allows_all(sample_images_dir):
    """Test that max_depth=None allows traversal to any depth."""
    images = walk_directory(sample_images_dir, recursive=True, max_depth=None)

    # Should find all 7 images including deeply nested ones
    assert len(images) == 7

    # Should include the deeply nested file
    relative_paths = {img.relative_path for img in images}
    assert "2021/projects/circuit_design/sketch_01.jpeg" in relative_paths


def test_max_depth_zero_root_only(sample_images_dir):
    """Test that max_depth=0 only finds files directly in root (no subdirs)."""
    # First, create a file directly in the root
    (sample_images_dir / "root_image.jpg").write_bytes(b"root level image")

    images = walk_directory(sample_images_dir, recursive=True, max_depth=0)

    # Should only find files directly in root with no subdirectories
    relative_paths = {img.relative_path for img in images}
    expected = {
        "root_image.jpg",
    }
    assert relative_paths == expected
    assert len(images) == 1


def test_max_depth_one(sample_images_dir):
    """Test that max_depth=1 limits to one subdirectory level."""
    images = walk_directory(sample_images_dir, recursive=True, max_depth=1)

    relative_paths = {img.relative_path for img in images}
    # max_depth=1 means depth <= 1, so files with at most 1 directory level
    # Only root_level/* files are at depth 1
    # 2020/january/* are at depth 2, so excluded
    expected = {
        "root_level/document.TIFF",
        "root_level/photo.WebP",
    }
    assert relative_paths == expected
    assert len(images) == 2


def test_max_depth_two(sample_images_dir):
    """Test that max_depth=2 allows two subdirectory levels."""
    images = walk_directory(sample_images_dir, recursive=True, max_depth=2)

    relative_paths = {img.relative_path for img in images}
    # max_depth=2 means depth <= 2
    # Files at 2021/projects/circuit_design/* are at depth 3, so should be excluded
    # But files at 2020/january/* are at depth 2, so included
    expected = {
        "2020/january/page_001.jpg",
        "2020/january/page_002.png",
        "2020/february/page_001.jpg",
        "root_level/document.TIFF",
        "root_level/photo.WebP",
    }
    assert relative_paths == expected
    assert len(images) == 5


def test_max_depth_three(sample_images_dir):
    """Test that max_depth=3 allows three subdirectory levels."""
    images = walk_directory(sample_images_dir, recursive=True, max_depth=3)

    # Should find all files (max depth in structure is 3)
    assert len(images) == 7

    relative_paths = {img.relative_path for img in images}
    assert "2021/projects/circuit_design/sketch_01.jpeg" in relative_paths


def test_max_depth_ignored_when_non_recursive(sample_images_dir):
    """Test that max_depth is ignored when recursive=False."""
    images_no_max = walk_directory(sample_images_dir, recursive=False)
    images_with_max = walk_directory(sample_images_dir, recursive=False, max_depth=1)

    # Both should be the same since recursive=False
    assert len(images_no_max) == len(images_with_max)
    relative_paths_no_max = {img.relative_path for img in images_no_max}
    relative_paths_with_max = {img.relative_path for img in images_with_max}
    assert relative_paths_no_max == relative_paths_with_max


def test_walk_directory_returns_sorted_list(sample_images_dir):
    """Test that results are sorted by path."""
    images = walk_directory(sample_images_dir, recursive=True)
    paths = [img.relative_path for img in images]

    # Verify sorted order
    assert paths == sorted(paths)


def test_walk_directory_with_custom_extensions(sample_images_dir):
    """Test walk_directory with custom extension set."""
    custom_extensions = {".jpg", ".jpeg"}
    images = walk_directory(sample_images_dir, recursive=True, extensions=custom_extensions)

    relative_paths = {img.relative_path for img in images}
    # Should only find jpg and jpeg files
    expected = {
        "2020/january/page_001.jpg",
        "2020/february/page_001.jpg",
        "2021/projects/circuit_design/sketch_01.jpeg",
    }
    assert relative_paths == expected


def test_walk_empty_directory(tmp_path):
    """Test walk_directory on an empty directory."""
    images = walk_directory(tmp_path, recursive=True)
    assert len(images) == 0
    assert images == []


def test_walk_directory_no_matching_extensions(tmp_path):
    """Test walk_directory when no files match extensions."""
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.md").write_text("content")

    images = walk_directory(tmp_path, recursive=True)
    assert len(images) == 0


def test_dedup_filtering_return_values(sample_images_dir):
    """Test that filter_already_ingested returns correct tuple format."""
    images = walk_directory(sample_images_dir, recursive=True)
    new_images, skipped = filter_already_ingested(images, set())

    assert isinstance(new_images, list)
    assert isinstance(skipped, int)
    assert all(isinstance(img, DiscoveredImage) for img in new_images)


def test_relative_path_consistency(sample_images_dir):
    """Test that relative_path and folder_hierarchy are consistent."""
    images = walk_directory(sample_images_dir, recursive=True)

    for img in images:
        # Extract filename from relative_path (split by forward slash)
        parts = img.relative_path.split("/")
        filename = parts[-1]
        # Reconstruct path from hierarchy and filename
        reconstructed = "/".join(img.folder_hierarchy + [filename])
        assert reconstructed == img.relative_path
