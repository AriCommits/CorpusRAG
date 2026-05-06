"""Tests for the unified cross-platform CLI (cli.py + cli_dev.py)."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

# Ensure src/ is on the path (mirrors editable install)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import corpus
from cli_dev import dev


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Unified corpus group
# ---------------------------------------------------------------------------


class TestCorpusGroup:
    def test_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_all_subcommands(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["--help"])
        output = result.output
        for cmd in (
            "rag",
            "video",
            "orchestrate",
            "flashcards",
            "handwriting",
            "summaries",
            "quizzes",
            "db",
            "dev",
        ):
            assert cmd in output, f"Expected '{cmd}' in corpus --help output"

    def test_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["--version"])
        assert result.exit_code == 0
        # Should print something (version string)
        assert result.output.strip() != ""

    def test_unknown_command_fails(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["nonexistent-command"])
        assert result.exit_code != 0

    def test_rag_subgroup_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["rag", "--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output
        assert "query" in result.output

    def test_video_subgroup_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["video", "--help"])
        assert result.exit_code == 0
        assert "transcribe" in result.output

    def test_orchestrate_subgroup_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["orchestrate", "--help"])
        assert result.exit_code == 0

    def test_flashcards_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["flashcards", "--help"])
        assert result.exit_code == 0

    def test_handwriting_subgroup_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["handwriting", "--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output

    def test_summaries_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["summaries", "--help"])
        assert result.exit_code == 0

    def test_quizzes_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["quizzes", "--help"])
        assert result.exit_code == 0

    def test_dev_subgroup_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["dev", "--help"])
        assert result.exit_code == 0

    def test_db_subgroup_reachable(self, runner: CliRunner) -> None:
        result = runner.invoke(corpus, ["db", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output


# ---------------------------------------------------------------------------
# dev subgroup
# ---------------------------------------------------------------------------


class TestDevGroup:
    def test_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_commands(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["--help"])
        for cmd in ("setup", "test", "lint", "fmt", "build", "clean", "completion"):
            assert cmd in result.output, f"Expected '{cmd}' in dev --help output"

    def test_completion_bash(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["completion", "bash"])
        assert result.exit_code == 0
        assert "_CORPUS_COMPLETE=bash_source" in result.output

    def test_completion_zsh(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "_CORPUS_COMPLETE=zsh_source" in result.output

    def test_completion_fish(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["completion", "fish"])
        assert result.exit_code == 0
        assert "fish_source" in result.output

    def test_completion_powershell(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["completion", "powershell"])
        assert result.exit_code == 0
        assert "Out-String" in result.output

    def test_completion_invalid_shell_fails(self, runner: CliRunner) -> None:
        result = runner.invoke(dev, ["completion", "cmd"])
        assert result.exit_code != 0

    def test_setup_invokes_pip(self, runner: CliRunner) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(dev, ["setup"])
        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert sys.executable in call_args
        assert "pip" in call_args
        assert "install" in call_args

    def test_test_invokes_pytest(self, runner: CliRunner) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(dev, ["test"])
        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "pytest" in call_args

    def test_test_with_cov_flag(self, runner: CliRunner) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(dev, ["test", "--cov"])
        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "--cov=src" in call_args

    def test_lint_invokes_ruff_and_mypy(self, runner: CliRunner) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(dev, ["lint"])
        assert result.exit_code == 0
        # lint calls subprocess.run twice (ruff, mypy)
        assert mock_run.call_count == 2
        all_cmds = [str(call[0][0]) for call in mock_run.call_args_list]
        combined = " ".join(all_cmds)
        assert "ruff" in combined
        assert "mypy" in combined

    def test_fmt_invokes_ruff_format(self, runner: CliRunner) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(dev, ["fmt"])
        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "ruff" in call_args
        assert "format" in call_args

    def test_build_invokes_build_module(self, runner: CliRunner) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.invoke(dev, ["build"])
        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "build" in call_args

    def test_clean_removes_artifacts(self, runner: CliRunner, tmp_path: Path) -> None:
        # Create a fake __pycache__ inside tmp_path
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        pyc_file = pycache / "foo.pyc"
        pyc_file.write_text("fake")

        # Patch ROOT to tmp_path so clean() only looks in our temp dir
        import cli_dev

        original_root = cli_dev.ROOT
        cli_dev.ROOT = tmp_path
        try:
            result = runner.invoke(dev, ["clean"])
        finally:
            cli_dev.ROOT = original_root

        assert result.exit_code == 0
        assert "Cleaned" in result.output


# ---------------------------------------------------------------------------
# ROOT path sanity
# ---------------------------------------------------------------------------


class TestDevRoot:
    def test_root_is_repo_root(self) -> None:
        import cli_dev

        # ROOT should be the parent of src/
        assert (cli_dev.ROOT / "pyproject.toml").exists()
        assert (cli_dev.ROOT / "src").is_dir()
