"""Tests for top-level corpus ingest / ask / summarize commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli import corpus


def test_ingest_requires_collection() -> None:
    runner = CliRunner()
    result = runner.invoke(corpus, ["ingest", "."])
    assert result.exit_code != 0


def test_ask_delegates_to_kernel(tmp_path: Path) -> None:
    cfg = tmp_path / "base.yaml"
    cfg.write_text("llm: {model: test}\ndatabase: {mode: persistent}\n", encoding="utf-8")
    fake = MagicMock()
    fake.ask.return_value = "because notes"
    runner = CliRunner()
    with patch("kernel.Corpus.from_config_path", return_value=fake):
        result = runner.invoke(corpus, ["ask", "What is X?", "-c", "notes", "-f", str(cfg)])
    assert result.exit_code == 0
    fake.ask.assert_called_once()
    assert "because notes" in result.output


def test_summarize_delegates_to_kernel(tmp_path: Path) -> None:
    cfg = tmp_path / "base.yaml"
    cfg.write_text("llm: {model: test}\ndatabase: {mode: persistent}\n", encoding="utf-8")
    fake = MagicMock()
    fake.summarize.return_value = {"summary": "A short summary."}
    runner = CliRunner()
    with patch("kernel.Corpus.from_config_path", return_value=fake):
        result = runner.invoke(corpus, ["summarize", "-c", "notes", "-f", str(cfg)])
    assert result.exit_code == 0
    fake.summarize.assert_called_once()
    assert "A short summary." in result.output
