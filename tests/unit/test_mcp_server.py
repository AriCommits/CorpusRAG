"""Tests for MCP server creation and profile loading."""

import asyncio
import pytest
import yaml
from mcp_server import create_mcp_server


@pytest.fixture()
def config_file(tmp_path):
    cfg = {
        "llm": {"model": "test"},
        "database": {"mode": "persistent", "persist_directory": str(tmp_path / "chroma")},
    }
    path = tmp_path / "base.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


class TestCreateMcpServer:
    def test_creates_server(self, config_file):
        server = create_mcp_server(config_file)
        assert server is not None
        assert server.name == "CorpusRAG"

    def test_dev_profile(self, config_file):
        server = create_mcp_server(config_file, profile="dev")
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "rag_query" in names
        assert "store_text" in names
        assert "generate_flashcards" not in names

    def test_learn_profile(self, config_file):
        server = create_mcp_server(config_file, profile="learn")
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "generate_flashcards" in names
        assert "rag_query" not in names

    def test_full_profile(self, config_file):
        server = create_mcp_server(config_file, profile="full")
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "rag_query" in names
        assert "generate_flashcards" in names

    def test_default_profile_is_full(self, config_file):
        server = create_mcp_server(config_file)
        names = [t.name for t in asyncio.run(server.list_tools())]
        assert "rag_query" in names
        assert "generate_flashcards" in names
