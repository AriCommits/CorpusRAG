"""End-to-end integration tests for MCP server stdio transport."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from mcp.server.fastmcp import FastMCP

from config import load_config
from db import ChromaDBBackend
from mcp_server.profiles import register_profile
from mcp_server.tools.common import init_config, init_db
from mcp_server.tools.dev import store_text

SRC_DIR = str(Path(__file__).parent.parent.parent / "src")


@pytest.fixture()
def stdio_config(tmp_path):
    cfg = {
        "llm": {"model": "test-model"},
        "database": {"mode": "persistent", "persist_directory": str(tmp_path / "chroma")},
        "rag": {
            "chunking": {"child_chunk_size": 200, "child_chunk_overlap": 20},
            "retrieval": {"top_k_semantic": 5, "top_k_bm25": 5, "top_k_final": 5, "rrf_k": 60},
            "parent_store": {"type": "local_file", "path": str(tmp_path / "parents")},
            "collection_prefix": "rag",
        },
    }
    path = tmp_path / "test_config.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


def _get_tool_names(mcp: FastMCP) -> list[str]:
    return [t.name for t in asyncio.run(mcp.list_tools())]


class TestStdioServerStarts:
    def test_server_starts_with_dev_profile(self, stdio_config):
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.server", "--profile", "dev", "--transport", "stdio", "--config", stdio_config],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=SRC_DIR,
        )
        try:
            time.sleep(2)
            assert proc.poll() is None, f"Server exited early: {proc.stderr.read().decode()}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_server_starts_with_learn_profile(self, stdio_config):
        proc = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.server", "--profile", "learn", "--transport", "stdio", "--config", stdio_config],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=SRC_DIR,
        )
        try:
            time.sleep(2)
            assert proc.poll() is None, f"Server exited early: {proc.stderr.read().decode()}"
        finally:
            proc.terminate()
            proc.wait(timeout=5)


class TestDevProfileTools:
    def test_dev_profile_has_store_text(self, stdio_config):
        config = load_config(stdio_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "dev", config, db)
        names = _get_tool_names(mcp)
        assert "store_text" in names
        assert "rag_query" in names
        assert "generate_flashcards" not in names

    def test_learn_profile_excludes_dev_tools(self, stdio_config):
        config = load_config(stdio_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "learn", config, db)
        names = _get_tool_names(mcp)
        assert "generate_flashcards" in names
        assert "store_text" not in names
        assert "rag_query" not in names


class TestStoreTextRoundTrip:
    def test_store_and_retrieve(self, stdio_config):
        config = load_config(stdio_config)
        db = ChromaDBBackend(config.database)

        with patch("mcp_server.tools.dev.EmbeddingClient") as MockEmbedder:
            MockEmbedder.return_value.embed_texts.return_value = [[0.1] * 384]
            result = store_text(
                "This is a test document about machine learning and neural networks.",
                "plans",
                config,
                db,
            )

        assert result["status"] == "success", f"store_text failed: {result.get('error')}"
        assert result["chunks_created"] >= 1

        assert db.collection_exists("rag_plans")
        assert db.count_documents("rag_plans") >= 1
