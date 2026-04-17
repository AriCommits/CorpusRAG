"""
MCP Server for CorpusRAG.

This module provides MCP (Model Context Protocol) server functionality,
exposing all CorpusRAG tools as callable functions for LLM agents.
"""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
