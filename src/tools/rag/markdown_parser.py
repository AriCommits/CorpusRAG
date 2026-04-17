"""Markdown parsing and semantic splitting for RAG."""

import re
from typing import Any

from langchain.schema import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter


HEADERS_TO_SPLIT = [
    ("#", "Document Title"),
    ("##", "Primary Section"),
    ("###", "Subsection"),
]


def extract_tags_from_text(text: str) -> tuple[str, list[str]]:
    """Extract #tags from bulleted lists in markdown.

    Tags are words starting with # that appear in lines beginning with - or *.
    Example:
        - #python #machine-learning #nlp
        - #rag #vector-search

    Args:
        text: Markdown text to extract tags from

    Returns:
        Tuple of (cleaned_text, tags_list) where tags_list contains unique tags
    """
    tags = set()
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Check if line is a bulleted list item
        if line.strip().startswith(("-", "*")):
            # Extract all #word patterns from this line
            tag_matches = re.findall(r"#(\w+)", line)
            if tag_matches:
                # This is a tag line — extract tags but don't keep the line
                tags.update(tag_matches)
                continue

        # Keep non-tag lines
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)
    return cleaned_text, sorted(list(tags))


def split_markdown_semantic(text: str) -> list[Document]:
    """Split markdown into semantic sections using header hierarchy.

    Splits on:
    - # (Document Title)
    - ## (Primary Section)
    - ### (Subsection)

    Extracts tags from bulleted lists and adds them to document metadata.

    Args:
        text: Markdown text to split

    Returns:
        List of LangChain Document objects with metadata
    """
    # First, extract tags globally from the entire document
    cleaned_text, global_tags = extract_tags_from_text(text)

    # Split by headers
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,
    )
    docs = splitter.split_text(cleaned_text)

    # Enrich metadata with tags
    for doc in docs:
        # Add global tags to all documents
        doc.metadata["tags"] = global_tags
        # Ensure metadata dict exists and is populated
        if not doc.metadata:
            doc.metadata = {}

    return docs


def parse_and_split(
    text: str, source_name: str | None = None
) -> list[dict[str, Any]]:
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
