"""Tests for MCP server functionality."""

import asyncio

import pytest
import yaml

from mcp_server import create_mcp_server


@pytest.fixture()
def config_file(tmp_path):
    """Write a minimal valid config for the MCP server."""
    cfg = {
        "llm": {"model": "llama3"},
        "database": {
            "mode": "persistent",
            "persist_directory": str(tmp_path / "chroma"),
        },
    }
    path = tmp_path / "base.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


def test_create_mcp_server(config_file):
    """Test MCP server creation."""
    server = create_mcp_server(config_file)
    assert server is not None
    assert server.name == "Corpus Callosum"


def test_mcp_server_has_rag_tools(config_file):
    """Test that MCP server exposes RAG tools."""
    server = create_mcp_server(config_file)
    tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
    assert "rag_ingest" in tool_names
    assert "rag_query" in tool_names
    assert "rag_retrieve" in tool_names


def test_mcp_server_has_flashcard_tools(config_file):
    """Test that MCP server exposes flashcard tools."""
    server = create_mcp_server(config_file)
    tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
    assert "generate_flashcards" in tool_names


def test_mcp_server_has_summary_tools(config_file):
    """Test that MCP server exposes summary tools."""
    server = create_mcp_server(config_file)
    tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
    assert "generate_summary" in tool_names


def test_mcp_server_has_quiz_tools(config_file):
    """Test that MCP server exposes quiz tools."""
    server = create_mcp_server(config_file)
    tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
    assert "generate_quiz" in tool_names


def test_mcp_server_has_video_tools(config_file):
    """Test that MCP server exposes video tools."""
    server = create_mcp_server(config_file)
    tool_names = [tool.name for tool in asyncio.run(server.list_tools())]
    assert "transcribe_video" in tool_names
    assert "clean_transcript" in tool_names


def test_mcp_server_has_resources(config_file):
    """Test that MCP server exposes resources."""
    server = create_mcp_server(config_file)
    resource_uris = [str(res.uri) for res in asyncio.run(server.list_resources())]
    assert "collections://list" in resource_uris


def test_mcp_server_has_prompts(config_file):
    """Test that MCP server exposes prompts."""
    server = create_mcp_server(config_file)
    prompt_names = [prompt.name for prompt in asyncio.run(server.list_prompts())]
    assert "study_session_prompt" in prompt_names
    assert "lecture_processing_prompt" in prompt_names
