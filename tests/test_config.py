"""Tests for configuration management."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from corpus_callosum.config import (
    PROJECT_ROOT,
    Config,
    _default_config_path,
    load_config,
)


def test_config_validation_creates_directories():
    """Test that config validation creates required directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vault_path = tmp_path / "test_vault"
        chroma_path = tmp_path / "test_chroma"

        # Create config data pointing to non-existent directories
        config_data = {
            "paths": {
                "vault": str(vault_path),
                "chromadb_store": str(chroma_path),
            }
        }

        # This should create the directories
        _config = Config.from_dict(
            config_data, project_root=tmp_path, config_path=tmp_path / "test_config.yaml"
        )

        # Verify directories were created
        assert vault_path.exists()
        assert chroma_path.exists()


def test_load_config_missing_file_error():
    """Test that helpful error is given when default config file is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Temporarily override the default config path to point to temp directory
        original_default_config_path = _default_config_path()

        # Monkey patch the _default_config_path function to return our temp path
        import corpus_callosum.config as config_module

        config_module._default_config_path = lambda: tmp_path / "configs" / "corpus_callosum.yaml"

        # Ensure file doesn't exist
        default_config_path = tmp_path / "configs" / "corpus_callosum.yaml"
        assert not default_config_path.exists()

        # Should raise helpful FileNotFoundError when using default path (no args, no env var)
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config()  # No args - should use default path

        assert "Configuration file not found" in str(exc_info.value)
        assert "Please copy the example config" in str(exc_info.value)

        # Restore the original function
        config_module._default_config_path = lambda: original_default_config_path


def test_load_config_explicit_missing_file():
    """Test that standard error is given when explicitly specified config file is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_path = tmp_path / "missing.yaml"

        # Ensure file doesn't exist
        assert not config_path.exists()

        # Should raise standard FileNotFoundError for explicit path
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config(str(config_path))

        assert "Configuration file not found" in str(exc_info.value)
        # Should NOT contain the helpful message for explicit paths
        assert "Please copy the example config" not in str(exc_info.value)


def test_load_config_with_env_var(monkeypatch):
    """Test that CORPUS_CALLOSUM_CONFIG environment variable works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        custom_config = tmp_path / "custom.yaml"
        # Use relative path in config (as users would typically do)
        custom_config.write_text("paths:\n  vault: ./custom_vault\n")

        # Set environment variable with absolute path to config file
        monkeypatch.setenv("CORPUS_CALLOSUM_CONFIG", str(custom_config.resolve()))

        # Load config should use the env var path
        config = load_config()
        # Relative paths in config are resolved relative to PROJECT_ROOT
        expected_vault_path = (PROJECT_ROOT / "custom_vault").resolve()
        assert config.paths.vault == expected_vault_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
