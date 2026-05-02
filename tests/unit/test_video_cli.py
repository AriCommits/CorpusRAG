"""Tests for video CLI commands."""

from click.testing import CliRunner

from tools.video.cli import video


def test_video_help():
    runner = CliRunner()
    result = runner.invoke(video, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.output
    assert "ingest-url" in result.output
    assert "jobs" in result.output
    assert "status" in result.output


def test_ingest_help():
    runner = CliRunner()
    result = runner.invoke(video, ["ingest", "--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output
    assert "--threshold" in result.output
    assert "--model" in result.output


def test_ingest_url_help():
    runner = CliRunner()
    result = runner.invoke(video, ["ingest-url", "--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output


def test_jobs_empty():
    runner = CliRunner()
    result = runner.invoke(video, ["jobs"])
    assert result.exit_code == 0
    assert "No active jobs" in result.output


def test_status_not_found():
    runner = CliRunner()
    result = runner.invoke(video, ["status", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.output
