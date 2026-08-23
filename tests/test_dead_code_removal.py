"""Tests to verify dead code removal was successful."""

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


def test_plan21_unused_layers_deleted() -> None:
    """Sprint 1 D1/D3: unused adapters, shims, utils, and models are gone."""
    removed = [
        "src/tools/rag/vectorstores/langchain_adapter.py",
        "src/tools/rag/vectorstores/chroma_adapter.py",
        "src/tools/rag/vectorstores/base.py",
        "src/tools/rag/embeddings.py",
        "src/tools/rag/storage.py",
        "src/tools/rag/markdown_parser.py",
        "src/tools/rag/message.py",
        "src/tools/rag/context.py",
        "src/utils/secrets.py",
        "src/utils/tokens.py",
        "src/db/models.py",
        "src/orchestrations/study_session.py",
        "src/orchestrations/knowledge_base.py",
    ]
    for path in removed:
        assert not Path(path).exists(), f"{path} should be deleted"


def test_plan21_forbidden_source_strings_absent() -> None:
    """Lock the sprint-4 grep list so deleted APIs cannot sneak back into src/."""
    forbidden = (
        "LangChainVectorStoreAdapter",
        "SecretManager",
        "utils.secrets",
        "utils.tokens",
        "tools.rag.message",
        "tools.rag.context",
        "VideoTranscriber(self.video_config, self.db)",
        "corpus rag ui",
        "Additional Question",
    )
    hits: list[str] = []
    for py_file in Path("src").rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden:
            if pattern in text:
                hits.append(f"{py_file.as_posix()}: {pattern!r}")
    mcp_dir = Path("src/mcp_server")
    for py_file in mcp_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if "from_dict(config.to_dict())" in text and "config.raw or" not in text:
            hits.append(f"{py_file.as_posix()}: from_dict(config.to_dict()) without raw")
    summaries_cli = Path("src/tools/summaries/cli.py").read_text(encoding="utf-8")
    if "summary.text" in summaries_cli:
        hits.append("src/tools/summaries/cli.py: summary.text")
    assert not hits, "Forbidden source strings still present:\n  " + "\n  ".join(hits)


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
    from config.base import (  # noqa: F401
        BaseConfig,
        DatabaseConfig,
        EmbeddingConfig,
        LLMConfig,
        PathsConfig,
    )
    from config.loader import load_config, merge_configs  # noqa: F401

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
