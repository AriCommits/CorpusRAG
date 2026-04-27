import asyncio
import sys
import types
import pytest
import yaml
from mcp.server.fastmcp import FastMCP


def _stub_mcp_server_init():
    """Stub out mcp_server.__init__ to avoid the broken server/auth import chain."""
    if "mcp_server" not in sys.modules:
        stub = types.ModuleType("mcp_server")
        sys.modules["mcp_server"] = stub


@pytest.fixture(autouse=True)
def _patch_mcp_server_init():
    _stub_mcp_server_init()


@pytest.fixture()
def profile_config(tmp_path):
    cfg = {"llm": {"model": "test"}, "database": {"mode": "persistent", "persist_directory": str(tmp_path / "chroma")}}
    path = tmp_path / "base.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


def _get_tool_names(mcp):
    return [t.name for t in asyncio.run(mcp.list_tools())]


class TestRegisterProfile:
    def test_dev_profile_has_rag_tools(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile
        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "dev", config, db)
        names = _get_tool_names(mcp)
        assert "rag_query" in names
        assert "store_text" in names
        assert "generate_flashcards" not in names

    def test_learn_profile_has_learn_tools(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile
        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "learn", config, db)
        names = _get_tool_names(mcp)
        assert "generate_flashcards" in names
        assert "rag_query" not in names

    def test_full_profile_has_everything(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile
        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "full", config, db)
        names = _get_tool_names(mcp)
        assert "rag_query" in names
        assert "store_text" in names
        assert "generate_flashcards" in names

    def test_invalid_profile_raises(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile
        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        with pytest.raises(ValueError, match="Unknown profile"):
            register_profile(mcp, "invalid", config, db)
