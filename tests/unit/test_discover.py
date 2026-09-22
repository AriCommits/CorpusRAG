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


def test_skips_symlink_file(tmp_path):
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"fake")
    inside = tmp_path / "in"
    inside.mkdir()
    real = inside / "real.mp4"
    real.write_bytes(b"fake")
    link = inside / "alias.mp4"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not permitted")

    result = discover_media_files(inside, EXTS)

    assert result == [real]


def test_directory_with_only_symlinks_raises(tmp_path):
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"fake")
    inside = tmp_path / "in"
    inside.mkdir()
    link = inside / "alias.mp4"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not permitted")

    with pytest.raises(FileNotFoundError):
        discover_media_files(inside, EXTS)


def test_symlink_file_as_root_raises(tmp_path):
    target = tmp_path / "target.mp4"
    target.write_bytes(b"fake")
    link = tmp_path / "link.mp4"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks not permitted")

    with pytest.raises(FileNotFoundError, match="Unsupported file format"):
        discover_media_files(link, EXTS)


def test_skips_symlink_file_mocked(tmp_path, monkeypatch):
    inside = tmp_path / "in"
    inside.mkdir()
    real = inside / "real.mp4"
    real.write_bytes(b"fake")
    fake_link = inside / "alias.mp4"
    fake_link.write_bytes(b"fake")

    from pathlib import Path

    orig_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: True if self.name == "alias.mp4" else orig_is_symlink(self),
    )

    result = discover_media_files(inside, EXTS)

    assert result == [real]


def test_skips_symlink_directory_outside_tree(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "hidden.mp4").write_bytes(b"fake")
    root = tmp_path / "root"
    root.mkdir()
    link = root / "link"
    try:
        link.symlink_to(other)
    except OSError:
        pytest.skip("symlinks not permitted")

    with pytest.raises(FileNotFoundError):
        discover_media_files(root, EXTS)


def test_max_files_raises(tmp_path):
    for name in ("a.mp4", "b.mp4", "c.mp4"):
        (tmp_path / name).write_bytes(b"fake")

    with pytest.raises(RuntimeError, match="more than 2 media files"):
        discover_media_files(tmp_path, EXTS, max_files=2)
