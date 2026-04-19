"""Markdown parsing for RAG (backward compatibility shim)."""

from .pipeline.parsers import (
    ParsedTag,
    build_tag_metadata,
    extract_tags_from_text,
    parse_and_split,
    parse_hierarchical_tags,
    split_markdown_semantic,
)

__all__ = [
    "ParsedTag",
    "parse_hierarchical_tags",
    "build_tag_metadata",
    "extract_tags_from_text",
    "split_markdown_semantic",
    "parse_and_split",
]
