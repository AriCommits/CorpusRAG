"""CorpusRAG MCP Server.

Thin orchestrator wiring together tool profiles, transport, and middleware.
"""

import argparse
import logging

from mcp.server.fastmcp import FastMCP

from .profiles import VALID_PROFILES, register_profile
from .tools.common import init_config, init_db

logger = logging.getLogger(__name__)


def create_mcp_server(
    config_path: str | None = None,
    profile: str = "full",
) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        config_path: Path to config YAML. Defaults to configs/base.yaml.
        profile: Tool profile - 'dev', 'learn', or 'full'.

    Returns:
        Configured FastMCP server instance.
    """
    config = init_config(config_path)
    db = init_db(config)

    mcp = FastMCP("CorpusRAG", json_response=True)
    register_profile(mcp, profile, config, db)

    logger.info("MCP server created with profile='%s'", profile)
    return mcp


def main() -> None:
    """CLI entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="CorpusRAG MCP Server")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument(
        "--profile",
        choices=list(VALID_PROFILES),
        default="full",
        help="Tool profile (default: full)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host (HTTP only)")
    parser.add_argument("--port", type=int, default=8000, help="Port (HTTP only)")
    parser.add_argument(
        "--no-auth", action="store_true", help="Disable auth (HTTP only)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    mcp = create_mcp_server(args.config, args.profile)

    if args.transport == "streamable-http":
        from .middleware import apply_http_middleware

        apply_http_middleware(mcp, auth_enabled=not args.no_auth)
        logger.info(
            "Starting CorpusRAG MCP (HTTP) on %s:%d [profile=%s]",
            args.host, args.port, args.profile,
        )
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        logger.info("Starting CorpusRAG MCP (stdio) [profile=%s]", args.profile)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
