"""Markdown parsing and semantic splitting for RAG."""

import re
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

HEADERS_TO_SPLIT = [
    ("#", "Document Title"),
    ("##", "Primary Section"),
    ("###", "Subsection"),
]


@dataclass(frozen=True)
class ParsedTag:
    """A parsed hierarchical tag.

    Example:
        full="Skill/Data_Based_Statistical_Reasoning"
        parts=["Skill", "Data_Based_Statistical_Reasoning"]
        prefix="Skill"
        leaf="Data_Based_Statistical_Reasoning"
    """

    full: str  # "Skill/Data_Based_Statistical_Reasoning"
    parts: list[str]  # ["Skill", "Data_Based_Statistical_Reasoning"]
    prefix: str  # "Skill" (top-level)
    leaf: str  # "Data_Based_Statistical_Reasoning" (most specific)


def parse_hierarchical_tags(content: str) -> list[ParsedTag]:
    """Extract hierarchical tags (#Subject/Subtopic) from markdown.

    Supports:
    - Flat tags: #Python → ParsedTag(full="Python", prefix="Python", leaf="Python")
    - Hierarchical tags: #CS/ML → ParsedTag(full="CS/ML", prefix="CS", leaf="ML")
    - Deep hierarchy: #Subject/Area/Topic (max 3 levels)

    Args:
        content: Markdown content to extract tags from

    Returns:
        List of ParsedTag objects in sorted order
    """
    raw_tags = set()
    for line in content.split("\n"):
        if line.strip().startswith(("-", "*")):
            # Match #Word or #Word/Word/Word (max 3 levels)
            matches = re.findall(r"#([\w]+(?:/[\w]+){0,2})", line)
            raw_tags.update(matches)

    parsed = []
    for tag in sorted(raw_tags):
        parts = tag.split("/")
        parsed.append(
            ParsedTag(
                full=tag,
                parts=parts,
                prefix=parts[0],
                leaf=parts[-1],
            )
        )
    return parsed


def build_tag_metadata(tags: list[ParsedTag]) -> dict[str, list[str]]:
    """Build ChromaDB-compatible metadata from parsed tags.

    Creates three metadata fields:
    - tags: Full tag paths (e.g., ["Skill/ML", "Skill/Statistics"])
    - tag_prefixes: Top-level categories (e.g., ["Skill"])
    - tag_leaves: Most specific tags (e.g., ["ML", "Statistics"])

    Args:
        tags: List of ParsedTag objects

    Returns:
        Dict with keys "tags", "tag_prefixes", "tag_leaves" (all list[str])
    """
    if not tags:
        return {}
    return {
        "tags": [t.full for t in tags],
        "tag_prefixes": sorted({t.prefix for t in tags}),
        "tag_leaves": sorted({t.leaf for t in tags}),
    }


def extract_tags_from_text(text: str) -> tuple[str, dict[str, list[str]]]:
    """Extract hierarchical #tags from bulleted lists in markdown.

    Tags can be:
    - Flat: #python
    - Hierarchical: #Skill/Statistics
    - Deep: #Subject/Area/Topic (max 3 levels)

    Example:
        - #python #Skill/ML
        - #CS/Algorithms #Performance

    Args:
        text: Markdown text to extract tags from

    Returns:
        Tuple of (cleaned_text, tag_metadata_dict) where tag_metadata_dict
        contains "tags", "tag_prefixes", and "tag_leaves" fields
    """
    parsed_tags = parse_hierarchical_tags(text)
    tag_metadata = build_tag_metadata(parsed_tags)
    return text, tag_metadata


def split_markdown_semantic(text: str) -> list[Document]:
    """Split markdown into semantic sections using header hierarchy.

    Splits on:
    - # (Document Title)
    - ## (Primary Section)
    - ### (Subsection)

    Extracts hierarchical tags from bulleted lists and adds them to document metadata.

    Args:
        text: Markdown text to split

    Returns:
        List of LangChain Document objects with metadata
    """
    # First, extract tags globally from the entire document
    cleaned_text, tag_metadata = extract_tags_from_text(text)

    # Split by headers
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,
    )
    docs = splitter.split_text(cleaned_text)

    # Enrich metadata with tags
    for doc in docs:
        # Ensure metadata dict exists
        if not doc.metadata:
            doc.metadata = {}
        # Merge tag metadata fields into document metadata
        doc.metadata.update(tag_metadata)

    return docs


def parse_and_split(text: str, source_name: str | None = None) -> list[dict[str, Any]]:
    """Parse markdown, extract tags, and split into semantic sections.

    Args:
        text: Markdown text to parse
        source_name: Optional source file name for metadata

    Returns:
        List of dicts with 'text', 'metadata' keys compatible with RAG ingester
    """
    docs = split_markdown_semantic(text)

    result = []
    for i, doc in enumerate(docs):
        metadata = dict(doc.metadata) if doc.metadata else {}
        if source_name:
            metadata["source_file"] = source_name
        metadata["chunk_index"] = i

        result.append(
            {
                "text": doc.page_content,
                "metadata": metadata,
            }
        )

    return result
