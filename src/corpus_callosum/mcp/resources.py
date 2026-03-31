"""MCP resources for CorpusCallosum.

Exposes collection data as MCP resources that clients can read.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from .retriever import HybridRetriever

logger = logging.getLogger(__name__)


def register_resources(mcp: FastMCP, retriever: HybridRetriever) -> None:
    """Register all CorpusCallosum resources with the MCP server."""

    @mcp.resource("collection://{name}")
    def get_collection_content(name: str) -> str:
        """Read all documents in a collection.

        Args:
            name: The collection name
        """
        try:
            chunks = retriever.collection_documents(name)
            if not chunks:
                return f"Collection '{name}' is empty or does not exist."

            parts: list[str] = []
            for chunk in chunks:
                source = chunk.metadata.get("source_file", "unknown")
                parts.append(f"--- {source} ---\n{chunk.text}")
            return "\n\n".join(parts)
        except Exception as exc:
            logger.exception("get_collection_content failed")
            return f"Error reading collection '{name}': {exc}"

    @mcp.resource("collection://{name}/meta")
    def get_collection_meta(name: str) -> str:
        """Get metadata about a collection.

        Args:
            name: The collection name
        """
        try:
            chunks = retriever.collection_documents(name)
            if not chunks:
                return f"Collection '{name}' is empty or does not exist."

            sources: set[str] = set()
            total_chars = 0
            for chunk in chunks:
                source = chunk.metadata.get("source_file", "unknown")
                sources.add(source)
                total_chars += len(chunk.text)

            lines = [
                f"Collection: {name}",
                f"Total chunks: {len(chunks)}",
                f"Source files: {len(sources)}",
                f"Total characters: {total_chars}",
                "",
                "Sources:",
            ]
            lines.extend(f"- {s}" for s in sorted(sources))
            return "\n".join(lines)
        except Exception as exc:
            logger.exception("get_collection_meta failed")
            return f"Error reading collection metadata '{name}': {exc}"
