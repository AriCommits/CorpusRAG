"""Tests for Docker image slimming — verify server extra exists and excludes heavy deps."""

import sys
import pytest


class TestServerExtra:
    def test_server_extra_in_pyproject(self):
        """The server extra should exist in pyproject.toml."""
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        extras = data["project"]["optional-dependencies"]
        assert "server" in extras, "Missing 'server' extra in pyproject.toml"

    def test_server_extra_excludes_torch(self):
        """Server extra should not include torch or sentence-transformers."""
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        server_deps = data["project"]["optional-dependencies"]["server"]
        dep_names = [d.split(">=")[0].split("<")[0].split("[")[0].strip().lower() for d in server_deps]
        assert "torch" not in dep_names
        assert "sentence-transformers" not in dep_names
        assert "faster-whisper" not in dep_names
        assert "textual" not in dep_names

    def test_server_extra_has_core_deps(self):
        """Server extra should include fastapi, chromadb, mcp."""
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        server_deps = data["project"]["optional-dependencies"]["server"]
        dep_str = " ".join(server_deps).lower()
        assert "fastapi" in dep_str
        assert "chromadb" in dep_str
        assert "mcp" in dep_str
