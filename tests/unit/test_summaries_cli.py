"""CLI tests for the summaries command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from tools.summaries.cli import summaries


def test_summaries_cli_exports_dict_summary(tmp_path):
    runner = CliRunner()
    output = tmp_path / "out.md"
    fake_summary = {"summary": "A short summary.", "keywords": ["x"]}

    fake_cfg = MagicMock()
    fake_cfg.summary_length = "medium"
    fake_db = MagicMock()
    fake_generator = MagicMock()
    fake_generator.generate.return_value = fake_summary

    with (
        patch("tools.summaries.cli.load_cli_db", return_value=(fake_cfg, fake_db)),
        patch("tools.summaries.cli.SummaryGenerator", return_value=fake_generator),
    ):
        result = runner.invoke(
            summaries,
            ["-c", "notes", "-o", str(output), "--export", "markdown"],
        )

    assert result.exit_code == 0, result.output
    assert output.exists()
    assert "A short summary." in output.read_text(encoding="utf-8")
