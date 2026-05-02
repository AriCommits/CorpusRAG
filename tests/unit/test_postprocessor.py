"""Tests for video post-processing."""

from pathlib import Path

from tools.video.extractor import ExtractedFrame
from tools.video.postprocessor import (
    ProcessedChunk,
    build_chunk,
    deduplicate_chunks,
    format_chunk_markdown,
)


def _frame(idx: int, ts: float) -> ExtractedFrame:
    return ExtractedFrame(path=Path(f"frame_{idx}.jpg"), frame_index=idx, source_timestamp_sec=ts)


def test_build_chunk():
    chunk = build_chunk("Hello world", _frame(0, 10.0), "slide", Path("test.mp4"))
    assert chunk.content == "Hello world"
    assert chunk.frame_index == 0
    assert chunk.timestamp_str == "00:00:10"
    assert chunk.frame_type == "slide"
    assert len(chunk.content_hash) == 16


def test_build_chunk_hash_deterministic():
    c1 = build_chunk("same text", _frame(0, 0), "slide", Path("a.mp4"))
    c2 = build_chunk("same text", _frame(1, 5), "slide", Path("b.mp4"))
    assert c1.content_hash == c2.content_hash


def test_dedup_identical():
    chunks = [
        build_chunk("identical content here", _frame(i, i * 10.0), "slide", Path("t.mp4"))
        for i in range(3)
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 1


def test_dedup_different():
    chunks = [
        build_chunk("completely different text about topic A", _frame(0, 0), "slide", Path("t.mp4")),
        build_chunk("another unrelated paragraph about topic B", _frame(1, 10), "slide", Path("t.mp4")),
    ]
    result = deduplicate_chunks(chunks)
    assert len(result) == 2


def test_dedup_empty():
    assert deduplicate_chunks([]) == []


def test_format_chunk_markdown():
    chunk = build_chunk("# Slide Title", _frame(5, 125.0), "slide", Path("t.mp4"))
    md = format_chunk_markdown(chunk)
    assert "<!-- timestamp: 00:02:05 | frame: 5 -->" in md
    assert "# Slide Title" in md
