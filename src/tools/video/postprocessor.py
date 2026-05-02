"""Post-processing for video OCR output."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .extractor import ExtractedFrame, format_timestamp


@dataclass
class ProcessedChunk:
    content: str
    frame_index: int
    timestamp_sec: float
    timestamp_str: str
    source_file: str
    frame_type: str
    content_hash: str


def build_chunk(
    text: str,
    frame: ExtractedFrame,
    frame_type: str,
    source_file: Path,
) -> ProcessedChunk:
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return ProcessedChunk(
        content=text,
        frame_index=frame.frame_index,
        timestamp_sec=frame.source_timestamp_sec,
        timestamp_str=format_timestamp(frame.source_timestamp_sec),
        source_file=str(source_file),
        frame_type=frame_type,
        content_hash=content_hash,
    )


def deduplicate_chunks(
    chunks: list[ProcessedChunk], similarity_threshold: float = 0.85
) -> list[ProcessedChunk]:
    if not chunks:
        return []
    seen: list[ProcessedChunk] = [chunks[0]]
    for chunk in chunks[1:]:
        if _jaccard(chunk.content, seen[-1].content) < similarity_threshold:
            seen.append(chunk)
    return seen


def format_chunk_markdown(chunk: ProcessedChunk) -> str:
    return (
        f"<!-- timestamp: {chunk.timestamp_str} | frame: {chunk.frame_index} -->\n"
        f"{chunk.content}"
    )


def _jaccard(a: str, b: str) -> float:
    ngrams_a = set(_ngrams(a, 3))
    ngrams_b = set(_ngrams(b, 3))
    if not ngrams_a and not ngrams_b:
        return 1.0
    if not ngrams_a or not ngrams_b:
        return 0.0
    return len(ngrams_a & ngrams_b) / len(ngrams_a | ngrams_b)


def _ngrams(text: str, n: int) -> list[str]:
    text = text.lower().replace(" ", "")
    return [text[i : i + n] for i in range(len(text) - n + 1)]
