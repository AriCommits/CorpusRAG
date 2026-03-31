"""MCP server for CorpusCallosum.

Provides both stdio transport (for Claude Desktop, Cursor, etc.)
and HTTP/SSE transport (for remote clients).
"""

from __future__ import annotations

import argparse
import logging
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from ..agent import RagAgent
from ..config import get_config, load_config
from ..ingest import Ingester
from ..retriever import HybridRetriever
from .resources import register_resources
from .tools import register_tools

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

SERVER_NAME = "corpus-callosum"
SERVER_VERSION = "0.2.0"


def create_mcp_server(config_path: str | None = None) -> FastMCP:
    """Create an MCP server instance with all tools and resources."""
    if config_path:
        load_config(config_path)

    agent = RagAgent()
    ingester = Ingester()
    retriever = HybridRetriever()

    mcp = FastMCP(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=(
            "CorpusCallosum is a local-first RAG service. "
            "Use query_documents to ask questions about indexed documents. "
            "Use ingest_documents to add files to collections. "
            "Use list_collections to see what's available. "
            "Use summarize_collection for overviews. "
            "Use critique_writing for writing feedback. "
            "Use generate_flashcards for study materials."
        ),
    )

    register_tools(mcp, agent, ingester, retriever)
    register_resources(mcp, retriever)

    return mcp


def mount_mcp(app: FastAPI, config_path: str | None = None) -> None:
    """Mount MCP HTTP transport onto an existing FastAPI app."""
    mcp = create_mcp_server(config_path)
    mcp._api.mount_to_app(app, path="/mcp")


def run_stdio(config_path: str | None = None) -> None:
    """Run MCP server with stdio transport."""
    mcp = create_mcp_server(config_path)
    mcp.run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8081, config_path: str | None = None) -> None:
    """Run MCP server with HTTP transport."""
    import uvicorn

    mcp = create_mcp_server(config_path)
    app = mcp.streamable_http_app()
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """CLI entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="CorpusCallosum MCP Server")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="HTTP host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="HTTP port (default: 8081)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.transport == "stdio":
        run_stdio(config_path=args.config)
    else:
        run_http(host=args.host, port=args.port, config_path=args.config)


if __name__ == "__main__":
    main()
