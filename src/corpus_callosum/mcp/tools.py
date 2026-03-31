"""MCP tools for CorpusCallosum.

Exposes RAG capabilities as MCP tools that any MCP-compatible client can use.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from .agent import RagAgent
    from .ingest import Ingester
    from .retriever import HybridRetriever

logger = logging.getLogger(__name__)


def register_tools(
    mcp: FastMCP, agent: RagAgent, ingester: Ingester, retriever: HybridRetriever
) -> None:
    """Register all CorpusCallosum tools with the MCP server."""

    @mcp.tool()
    def query_documents(
        query: str,
        collection: str,
        model: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Query documents in a collection using RAG. Returns a complete answer based on your indexed documents.

        Args:
            query: The question to ask
            collection: The collection name to search
            model: Optional model override (e.g. "llama3", "mistral")
            session_id: Optional session ID for multi-turn conversation
        """
        try:
            tokens, chunks = agent.query(
                query=query,
                collection_name=collection,
                model=model,
                session_id=session_id,
            )
            response = "".join(tokens)
            if not response.strip():
                return "No response generated. The model may be unavailable or the context was insufficient."
            return response
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            logger.exception("query_documents failed")
            return f"Error querying documents: {exc}"

    @mcp.tool()
    def ingest_documents(file_path: str, collection: str) -> str:
        """Ingest documents from a file or directory into a collection.

        Args:
            file_path: Path to a file or directory to ingest
            collection: Target collection name
        """
        try:
            result = ingester.ingest_path(path=file_path, collection_name=collection)
            return (
                f"Ingested {result.files_indexed} files "
                f"({result.chunks_indexed} chunks) into collection '{result.collection}'."
            )
        except FileNotFoundError:
            return f"Error: File or directory not found: {file_path}"
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            logger.exception("ingest_documents failed")
            return f"Error ingesting documents: {exc}"

    @mcp.tool()
    def list_collections() -> str:
        """List all available document collections."""
        try:
            names = retriever.list_collections()
            if not names:
                return "No collections found. Ingest some documents first using ingest_documents."
            return "Available collections:\n" + "\n".join(f"- {name}" for name in names)
        except Exception as exc:
            logger.exception("list_collections failed")
            return f"Error listing collections: {exc}"

    @mcp.tool()
    def critique_writing(essay_text: str, model: str | None = None) -> str:
        """Get AI-powered writing critique and feedback.

        Args:
            essay_text: The text to critique
            model: Optional model override
        """
        try:
            tokens = agent.critique_writing(essay_text, model=model)
            response = "".join(tokens)
            if not response.strip():
                return "No critique generated. The model may be unavailable."
            return response
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            logger.exception("critique_writing failed")
            return f"Error generating critique: {exc}"

    @mcp.tool()
    def generate_flashcards(collection: str, model: str | None = None) -> str:
        """Generate study flashcards from a collection. Returns cards in 'question::answer' format.

        Args:
            collection: Collection name to generate flashcards from
            model: Optional model override
        """
        try:
            tokens = agent.generate_flashcards(collection, model=model)
            response = "".join(tokens)
            if not response.strip():
                return (
                    "No flashcards generated. The collection may be empty or the model unavailable."
                )
            return response
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            logger.exception("generate_flashcards failed")
            return f"Error generating flashcards: {exc}"

    @mcp.tool()
    def summarize_collection(collection: str, detail_level: str = "medium") -> str:
        """Summarize the content of a collection with key topics and takeaways.

        Args:
            collection: Collection name to summarize
            detail_level: Level of detail - 'brief', 'medium', or 'detailed'
        """
        try:
            chunks = retriever.collection_documents(collection)
            if not chunks:
                return f"No documents found in collection '{collection}'."

            context = "\n\n".join(chunk.text for chunk in chunks)
            limit = {"brief": 4000, "medium": 8000, "detailed": 16000}.get(detail_level, 8000)
            if len(context) > limit:
                context = context[:limit]

            prompt = (
                f"Provide a {detail_level} summary of the following source material. "
                "Include key topics, main takeaways, and important concepts. "
                "Structure the summary with clear headings.\n\n"
                f"Source material:\n{context}\n"
            )
            tokens = agent._stream_generation(prompt)
            response = "".join(tokens)
            if not response.strip():
                return "No summary generated. The model may be unavailable."
            return response
        except ValueError as exc:
            return f"Error: {exc}"
        except Exception as exc:
            logger.exception("summarize_collection failed")
            return f"Error summarizing collection: {exc}"
