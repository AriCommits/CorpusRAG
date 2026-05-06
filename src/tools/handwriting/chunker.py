"""Parent-child chunking for handwritten document pages."""

from dataclasses import dataclass

from src.tools.handwriting.postprocessor import ProcessedPage, build_chromadb_metadata


@dataclass
class HandwritingChildChunk:
    """A child chunk representing a page with context from neighboring pages."""

    content: str  # Windowed content (current page + neighbors)
    parent_id: str  # Link to parent folder document
    metadata: dict  # ChromaDB metadata (includes parent_id)


def build_child_chunks(
    pages: list[ProcessedPage],
    parent_id: str,
    context_window: int = 1,
) -> list[HandwritingChildChunk]:
    """
    Build child chunks with adjacent page context.

    Skips blank pages entirely (no chunk emitted). For each non-blank page i,
    creates a chunk with content from a context window (i - window to i + window),
    excluding blank pages from the window.

    Args:
        pages: List of ProcessedPage instances.
        parent_id: Parent document ID to attach to metadata.
        context_window: Number of adjacent non-blank pages to include.
                       context_window=0 → single page chunks.
                       context_window=1 → current page ± 1 neighbors.

    Returns:
        List of HandwritingChildChunk instances.
    """
    chunks = []

    for i, page in enumerate(pages):
        # Skip blank pages entirely
        if page.is_blank:
            continue

        # Build context window: [max(0, i-window) : min(len, i+window+1)]
        start = max(0, i - context_window)
        end = min(len(pages), i + context_window + 1)

        # Get context pages and filter out blanks
        context_pages = [p for p in pages[start:end] if not p.is_blank]

        # Join context pages with separator
        content_with_context = "\n\n---\n\n".join(p.content for p in context_pages)

        # Build metadata from anchor page (the current non-blank page i)
        metadata = build_chromadb_metadata(page)
        metadata["parent_id"] = parent_id

        chunks.append(
            HandwritingChildChunk(
                content=content_with_context,
                parent_id=parent_id,
                metadata=metadata,
            )
        )

    return chunks
