"""Tests for media file discovery (:mod:`tools.video.discover`)."""

import pytest

from tools.video.discover import discover_media_files

EXTS = [".mp4", ".mkv", ".mov"]


def test_resolve_single_valid_file(tmp_path):
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"fake")

    result = discover_media_files(video, EXTS)

    assert result == [video]


def test_single_valid_file_case_insensitive_suffix(tmp_path):
    video = tmp_path / "lecture.MP4"
    video.write_bytes(b"fake")

    result = discover_media_files(video, EXTS)

    assert result == [video]


def test_wrong_file_suffix_raises_with_supported_formats(tmp_path):
    doc = tmp_path / "notes.txt"
    doc.write_bytes(b"fake")

    with pytest.raises(FileNotFoundError) as exc:
        discover_media_files(doc, EXTS)

    message = str(exc.value)
    assert "Supported formats" in message
    for ext in EXTS:
        assert ext in message


def test_directory_recursive_nested(tmp_path):
    top = tmp_path / "top.mp4"
    top.write_bytes(b"fake")
    nested_dir = tmp_path / "week1" / "day2"
    nested_dir.mkdir(parents=True)
    nested = nested_dir / "deep.mkv"
    nested.write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS)

    assert result == sorted([top, nested])


def test_directory_recursive_mixed_case(tmp_path):
    upper = tmp_path / "A.MP4"
    lower = tmp_path / "b.mkv"
    mixed = tmp_path / "C.MoV"
    for f in (upper, lower, mixed):
        f.write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS)

    assert result == sorted([upper, lower, mixed])


def test_directory_recursive_shallow(tmp_path):
    """A recursive scan of a directory with only top-level files works."""
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mov"
    a.write_bytes(b"fake")
    b.write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS, recursive=True)

    assert result == sorted([a, b])


def test_directory_stable_sorted(tmp_path):
    names = ["c.mp4", "a.mp4", "b.mp4"]
    for name in names:
        (tmp_path / name).write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS)

    assert result == sorted(result)
    assert [p.name for p in result] == ["a.mp4", "b.mp4", "c.mp4"]


def test_directory_nonrecursive_flat_only(tmp_path):
    top = tmp_path / "top.mp4"
    top.write_bytes(b"fake")
    nested_dir = tmp_path / "sub"
    nested_dir.mkdir()
    (nested_dir / "deep.mp4").write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS, recursive=False)

    assert result == [top]


def test_empty_directory_raises_compatible_shape(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        discover_media_files(tmp_path, EXTS)

    message = str(exc.value)
    assert "No supported media files found in" in message
    assert str(tmp_path) in message
    assert "Supported formats:" in message
    assert ", ".join(EXTS) in message


def test_directory_with_no_matching_extensions_raises(tmp_path):
    (tmp_path / "notes.txt").write_bytes(b"fake")
    (tmp_path / "image.png").write_bytes(b"fake")

    with pytest.raises(FileNotFoundError):
        discover_media_files(tmp_path, EXTS)


def test_recursive_skips_git_pycache_scratch(tmp_path):
    kept = tmp_path / "keep.mp4"
    kept.write_bytes(b"fake")

    for excluded in (".git", "__pycache__", "scratch"):
        d = tmp_path / excluded
        d.mkdir()
        (d / "hidden.mp4").write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS)

    assert result == [kept]


def test_recursive_skips_nested_excluded_dir(tmp_path):
    kept = tmp_path / "week1" / "keep.mp4"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(b"fake")

    buried = tmp_path / "week1" / ".git" / "buried.mp4"
    buried.parent.mkdir(parents=True)
    buried.write_bytes(b"fake")

    result = discover_media_files(tmp_path, EXTS)

    assert result == [kept]


def test_extensions_normalized_without_leading_dot(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")

    result = discover_media_files(tmp_path, ["mp4", "mkv"])

    assert result == [video]


def test_nonexistent_path_raises(tmp_path):
    missing = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        discover_media_files(missing, EXTS)
