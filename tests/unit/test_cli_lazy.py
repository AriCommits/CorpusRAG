"""Tests for LazyGroup short-help rendering without importing subcommands (A1).

These tests verify that ``LazyGroup``:

- accepts both ``str`` and ``tuple[str, str]`` entries in ``lazy_subcommands``,
- normalizes them via ``_spec``,
- renders the ``Commands`` help section from stored short help without importing
  the subcommand modules (``format_commands`` never calls ``_load_lazy``), and
- still lazily loads real subcommands when a command is actually invoked.
"""

import sys
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

# Ensure src/ is on the path (mirrors editable install)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import corpus
from cli_lazy import LazyGroup


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# _spec normalization + both value shapes
# ---------------------------------------------------------------------------


class TestSpecNormalization:
    def test_string_entry_has_empty_short_help(self) -> None:
        group = LazyGroup(name="root", lazy_subcommands={"foo": "pkg.mod:foo"})
        assert group._spec("foo") == ("pkg.mod:foo", "")

    def test_tuple_entry_returns_import_path_and_help(self) -> None:
        group = LazyGroup(
            name="root",
            lazy_subcommands={"bar": ("pkg.mod:bar", "Bar does things.")},
        )
        assert group._spec("bar") == ("pkg.mod:bar", "Bar does things.")

    def test_list_commands_includes_both_shapes(self) -> None:
        group = LazyGroup(
            name="root",
            lazy_subcommands={
                "foo": "pkg.mod:foo",
                "bar": ("pkg.mod:bar", "Bar."),
            },
        )
        ctx = click.Context(group)
        names = group.list_commands(ctx)
        assert "foo" in names
        assert "bar" in names


# ---------------------------------------------------------------------------
# format_commands must not import subcommands
# ---------------------------------------------------------------------------


class TestFormatCommandsNoImport:
    def test_format_commands_does_not_call_load_lazy(self) -> None:
        group = LazyGroup(
            name="root",
            help="Root group.",
            lazy_subcommands={
                "foo": ("pkg.does_not_exist:foo", "Foo short help."),
                "bar": "pkg.also_missing:bar",
            },
        )

        called: list[str] = []

        def _boom(cmd_name: str):  # pragma: no cover - should never run
            called.append(cmd_name)
            raise AssertionError("format_commands must not import subcommands")

        group._load_lazy = _boom  # type: ignore[method-assign]

        ctx = click.Context(group)
        formatter = ctx.make_formatter()
        group.format_commands(ctx, formatter)
        output = formatter.getvalue()

        assert called == []
        # Stored short help is rendered; missing modules are never imported.
        assert "Foo short help." in output
        assert "foo" in output
        assert "bar" in output

    def test_string_entry_renders_without_short_help_text(self) -> None:
        group = LazyGroup(
            name="root",
            lazy_subcommands={"bar": "pkg.also_missing:bar"},
        )
        group._load_lazy = lambda name: (_ for _ in ()).throw(  # type: ignore[method-assign]
            AssertionError("should not import")
        )
        ctx = click.Context(group)
        formatter = ctx.make_formatter()
        group.format_commands(ctx, formatter)
        output = formatter.getvalue()
        assert "bar" in output


# ---------------------------------------------------------------------------
# Real corpus help output uses stored short help + still lists commands
# ---------------------------------------------------------------------------


class TestCorpusHelpShortHelp:
    def test_root_help_lists_all_commands(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["--help"])
        assert result.exit_code == 0
        for cmd in (
            "tools",
            "db",
            "collections",
            "dev",
            "orchestrate",
            "setup",
            "benchmark",
            "doctor",
        ):
            assert cmd in result.output, f"Expected '{cmd}' in corpus --help"

    def test_root_help_shows_lazy_short_help(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["--help"])
        assert result.exit_code == 0
        assert "Database management commands." in result.output
        assert "Manage vector database collections." in result.output
        assert "Orchestration workflows for CorpusRAG." in result.output

    def test_root_help_does_not_import_rag_or_video(self, runner: CliRunner) -> None:
        # A1 alone: rendering root help must not import the RAG/video Click
        # modules (their heavy deps). db.management may still be imported until
        # A2/A3 land, so it is intentionally not asserted here.
        for mod in ("tools.rag.cli", "tools.video.cli"):
            sys.modules.pop(mod, None)
        result = runner.invoke(corpus, ["--help"])
        assert result.exit_code == 0
        assert "tools.rag.cli" not in sys.modules
        assert "tools.video.cli" not in sys.modules

    def test_tools_help_shows_lazy_short_help(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["tools", "--help"])
        assert result.exit_code == 0
        assert "RAG (Retrieval-Augmented Generation) tool." in result.output
        assert "Video transcription and processing tool." in result.output
        assert "Handwritten document ingestion tools." in result.output

    def test_learning_help_shows_lazy_short_help(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["tools", "learning", "--help"])
        assert result.exit_code == 0
        assert "Generate flashcards from a collection." in result.output
        assert "Generate quiz questions from a collection." in result.output

    def test_subcommand_still_lazy_loads_on_invoke(self, runner: CliRunner) -> None:
        # Actually running a lazy subcommand must still resolve the real group.
        result = runner.invoke(corpus, ["tools", "rag", "--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output
