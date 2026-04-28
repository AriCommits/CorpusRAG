"""Adaptive content-aware text splitter for RAG child chunks."""

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class ChunkParams:
    """Parameters for a specific content type."""
    chunk_size: int
    chunk_overlap: int
    separators: list[str]


PRESETS = {
    "code": ChunkParams(800, 100, ["\n\n", "\n"]),
    "list": ChunkParams(600, 50, ["\n\n", "\n- ", "\n* ", "\n1. ", "\n"]),
    "prose": ChunkParams(500, 75, ["\n\n", ". ", "\n", " "]),
    "short": ChunkParams(0, 0, []),
    "default": ChunkParams(400, 50, ["\n\n", "\n", " ", ""]),
}


def classify_content(text: str) -> str:
    """Classify text content type using simple heuristics."""
    lines = text.split("\n")
    non_empty = [l for l in lines if l.strip()]

    if not non_empty:
        return "short"

    # Check structural signals before length gate so small code/list blocks
    # are classified correctly.
    code_fences = text.count("```")
    indented = sum(1 for l in non_empty if l.startswith("    ") or l.startswith("\t"))
    if code_fences >= 2 or (indented / len(non_empty)) > 0.4:
        return "code"

    list_lines = sum(1 for l in non_empty if re.match(r"^\s*[-*]\s|^\s*\d+\.\s", l))
    if (list_lines / len(non_empty)) > 0.4:
        return "list"

    if len(text) < 400:
        return "short"

    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    avg_sentence_len = len(words) / max(len(sentences), 1)
    if avg_sentence_len > 20 and len(non_empty) < len(words) / 10:
        return "prose"

    return "default"


def adaptive_split(text: str, base_chunk_size: int = 400, base_overlap: int = 50) -> list[str]:
    """Split text using content-aware parameters."""
    content_type = classify_content(text)
    params = PRESETS[content_type]

    if content_type == "short":
        return [text] if text.strip() else []

    if content_type == "default":
        params = ChunkParams(base_chunk_size, base_overlap, params.separators)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=params.chunk_size,
        chunk_overlap=params.chunk_overlap,
        separators=params.separators,
    )
    return splitter.split_text(text)
