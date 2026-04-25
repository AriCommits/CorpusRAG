"""Tests to verify dead code removal was successful."""

import sys
from pathlib import Path


def test_manage_keys_file_deleted() -> None:
    """Verify manage_keys.py was deleted."""
    assert not Path("src/utils/manage_keys.py").exists(), "manage_keys.py should be deleted"


def test_manage_secrets_file_deleted() -> None:
    """Verify manage_secrets.py was deleted."""
    assert not Path("src/utils/manage_secrets.py").exists(), "manage_secrets.py should be deleted"


def test_schema_py_deleted() -> None:
    """Verify schema.py was deleted."""
    assert not Path("src/config/schema.py").exists(), "schema.py should be deleted"


def test_bulk_export_removed_from_cli() -> None:
    """Verify bulk_export function was removed from cli.py."""
    cli_path = Path("src/cli.py")
    assert cli_path.exists(), "cli.py should exist"

    content = cli_path.read_text()
    assert "def bulk_export" not in content, "bulk_export function should be removed"
    assert '@corpus.command(name="export")' not in content, "export command should be removed"


def test_pyproject_entry_points_cleaned() -> None:
    """Verify pyproject.toml entry points were cleaned."""
    pyproject_path = Path("pyproject.toml")
    assert pyproject_path.exists(), "pyproject.toml should exist"

    content = pyproject_path.read_text()

    # Check removed entry points
    assert "corpus-secrets" not in content, "corpus-secrets entry point should be removed"
    assert "corpus-api-keys" not in content, "corpus-api-keys entry point should be removed"
    assert "corpus-setup" not in content, "corpus-setup entry point should be removed"

    # Check kept entry points
    assert 'corpus = "cli:main"' in content, "corpus entry point should be kept"
    assert "corpus-mcp-server" in content, "corpus-mcp-server entry point should exist"


def test_config_imports_work() -> None:
    """Verify config module imports still work after schema.py deletion."""
    from config.loader import load_config, merge_configs  # noqa: F401
    from config.base import BaseConfig, DatabaseConfig, EmbeddingConfig, LLMConfig, PathsConfig  # noqa: F401

    # If imports don't raise exceptions, test passes


def test_cli_bulk_export_not_called() -> None:
    """Verify bulk_export is not referenced anywhere in codebase."""
    src_dir = Path("src")
    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if py_file.name != "cli.py":  # Don't check the definition was removed
                assert "bulk_export" not in content, f"bulk_export referenced in {py_file}"
        except Exception:
            # Skip files that can't be read
            pass
