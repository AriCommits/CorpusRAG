"""Tests for video CLI commands.

The heavy transcription / cleaning stack is never imported here: discovery and
the transcription queue are mocked at the ``tools.video.cli`` module level, and
``VideoTranscriber`` / ``TranscriptCleaner`` are replaced with light fakes. This
also guards the lazy-import contract — importing ``tools.video.cli`` and running
``--help`` must not pull in Whisper/torch/LLM implementations.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from click.testing import CliRunner

from tools.video import cli as video_cli
from tools.video.cli import video

# --------------------------------------------------------------------------- #
# Fakes / helpers
# --------------------------------------------------------------------------- #


@dataclass
class FakeResult:
    """Mirrors ``pipeline_queue.TranscriptJobResult`` for CLI tests."""

    source: Path
    parent: Path
    raw: str | None = None
    cleaned: str | None = None
    error: str | None = None


def make_result(path, *, raw="raw", cleaned=None, error=None):
    p = Path(path)
    return FakeResult(source=p, parent=p.parent, raw=raw, cleaned=cleaned, error=error)


class FakePaths:
    def __init__(self, base: Path):
        self.output_dir = base / "out"
        self.scratch_dir = base / "scratch"


class FakeConfig:
    """Minimal stand-in for VideoConfig used by the CLI."""

    def __init__(self, base: Path, max_concurrent_jobs=2):
        self.paths = FakePaths(base)
        self.max_concurrent_jobs = max_concurrent_jobs
        self.supported_extensions = [".mp4", ".mkv"]


class FakeTranscriber:
    """Light transcriber double; only ``combine_transcripts`` is exercised."""

    instances = []

    def __init__(self, cfg):
        self.cfg = cfg
        FakeTranscriber.instances.append(self)

    def combine_transcripts(self, transcripts, course=None, lecture=None):
        return "\n".join(f"{name}:{text}" for name, text in transcripts.items())


class FakeCleaner:
    instances = []

    def __init__(self, cfg):
        self.cfg = cfg
        FakeCleaner.instances.append(self)


@pytest.fixture(autouse=True)
def _reset_fakes():
    FakeTranscriber.instances = []
    FakeCleaner.instances = []
    yield


@pytest.fixture
def wired(monkeypatch, tmp_path):
    """Patch discovery/queue/config/transcriber/cleaner on the CLI module.

    Returns a dict with knobs the test can adjust (``files``, ``results``,
    ``recorded`` for captured queue kwargs).
    """
    cfg = FakeConfig(tmp_path)

    state = {
        "files": [],
        "results": [],
        "recorded": {},
        "cfg": cfg,
    }

    def fake_load_cli_config(config_path, config_class):
        return cfg

    def fake_discover(root, extensions, *, recursive=True):
        state["recorded"]["recursive"] = recursive
        state["recorded"]["root"] = Path(root)
        return list(state["files"])

    def fake_queue(files, *, transcriber, cleaner, skip_clean, max_workers):
        state["recorded"]["skip_clean"] = skip_clean
        state["recorded"]["max_workers"] = max_workers
        state["recorded"]["cleaner_is_none"] = cleaner is None
        return list(state["results"])

    monkeypatch.setattr(video_cli, "load_cli_config", fake_load_cli_config, raising=False)
    monkeypatch.setattr(video_cli, "VideoConfig", FakeConfig, raising=False)
    monkeypatch.setattr(video_cli, "discover_media_files", fake_discover, raising=False)
    monkeypatch.setattr(video_cli, "run_transcription_queue", fake_queue, raising=False)
    monkeypatch.setattr(video_cli, "VideoTranscriber", FakeTranscriber, raising=False)
    monkeypatch.setattr(video_cli, "TranscriptCleaner", FakeCleaner, raising=False)

    return state


# --------------------------------------------------------------------------- #
# Help / startup (lazy-import contract)
# --------------------------------------------------------------------------- #


def test_video_help():
    runner = CliRunner()
    result = runner.invoke(video, ["--help"])
    assert result.exit_code == 0
    for cmd in ("transcribe", "pipeline", "ingest", "ingest-url", "jobs", "status"):
        assert cmd in result.output


def test_transcribe_help_lists_new_options():
    runner = CliRunner()
    result = runner.invoke(video, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "--no-recursive" in result.output
    assert "--workers" in result.output
    assert "--clean" in result.output


def test_pipeline_help_lists_new_options():
    runner = CliRunner()
    result = runner.invoke(video, ["pipeline", "--help"])
    assert result.exit_code == 0
    assert "--no-recursive" in result.output
    assert "--workers" in result.output
    assert "--skip-clean" in result.output
    assert "--augment" in result.output


def test_help_does_not_import_heavy_stack():
    """`--help` must not import transcribe/clean/augment implementations."""
    for mod in (
        "tools.video.transcribe",
        "tools.video.clean",
        "tools.video.augment",
        "tools.video.pipeline_queue",
        "tools.video.discover",
    ):
        sys.modules.pop(mod, None)

    runner = CliRunner()
    result = runner.invoke(video, ["transcribe", "--help"])
    assert result.exit_code == 0

    for mod in ("tools.video.transcribe", "tools.video.clean", "tools.video.augment"):
        assert mod not in sys.modules, f"{mod} eagerly imported by --help"


# --------------------------------------------------------------------------- #
# transcribe: discovery + queue wiring
# --------------------------------------------------------------------------- #


def test_transcribe_default_recursive_and_workers(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4", raw="RAW")]

    runner = CliRunner()
    result = runner.invoke(video, ["transcribe", str(folder), "-f", "cfg.yaml"])

    assert result.exit_code == 0, result.output
    assert wired["recorded"]["recursive"] is True
    # default workers resolves to cfg.max_concurrent_jobs (2)
    assert wired["recorded"]["max_workers"] == 2
    assert "Queued 1 videos" in result.output
    assert "✓ a.mp4" in result.output


def test_transcribe_no_recursive_flag(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4")]

    runner = CliRunner()
    result = runner.invoke(
        video, ["transcribe", str(folder), "--no-recursive", "-f", "cfg.yaml"]
    )

    assert result.exit_code == 0, result.output
    assert wired["recorded"]["recursive"] is False


def test_transcribe_workers_override(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4")]

    runner = CliRunner()
    result = runner.invoke(
        video, ["transcribe", str(folder), "--workers", "5", "-f", "cfg.yaml"]
    )

    assert result.exit_code == 0, result.output
    assert wired["recorded"]["max_workers"] == 5


def test_transcribe_clean_flag_controls_skip_clean(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4", cleaned="CLEAN")]

    runner = CliRunner()
    # without --clean -> skip_clean True, cleaner is None
    result = runner.invoke(video, ["transcribe", str(folder), "-f", "cfg.yaml"])
    assert result.exit_code == 0, result.output
    assert wired["recorded"]["skip_clean"] is True
    assert wired["recorded"]["cleaner_is_none"] is True

    # with --clean -> skip_clean False, cleaner constructed
    result = runner.invoke(video, ["transcribe", str(folder), "--clean", "-f", "cfg.yaml"])
    assert result.exit_code == 0, result.output
    assert wired["recorded"]["skip_clean"] is False
    assert wired["recorded"]["cleaner_is_none"] is False
    assert len(FakeCleaner.instances) == 1


def test_transcribe_single_folder_legacy_output(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4", folder / "b.mp4"]
    wired["results"] = [
        make_result(folder / "a.mp4", raw="A"),
        make_result(folder / "b.mp4", raw="B"),
    ]

    runner = CliRunner()
    result = runner.invoke(video, ["transcribe", str(folder), "-f", "cfg.yaml"])

    assert result.exit_code == 0, result.output
    legacy = wired["cfg"].paths.output_dir / "transcript.md"
    assert legacy.exists()
    assert "a.mp4:A" in legacy.read_text(encoding="utf-8")


def test_transcribe_tree_writes_per_parent(wired, tmp_path):
    root = tmp_path / "course"
    p1 = root / "L1"
    p2 = root / "L2"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)
    wired["files"] = [p1 / "a.mp4", p2 / "b.mp4"]
    wired["results"] = [
        make_result(p1 / "a.mp4", raw="A"),
        make_result(p2 / "b.mp4", raw="B"),
    ]

    runner = CliRunner()
    result = runner.invoke(video, ["transcribe", str(root), "-f", "cfg.yaml"])

    assert result.exit_code == 0, result.output
    assert (p1 / "transcript.md").exists()
    assert (p2 / "transcript.md").exists()
    assert "a.mp4:A" in (p1 / "transcript.md").read_text(encoding="utf-8")
    assert "b.mp4:B" in (p2 / "transcript.md").read_text(encoding="utf-8")


def test_transcribe_partial_failure_exit_1_keeps_success(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4", folder / "b.mp4"]
    wired["results"] = [
        make_result(folder / "a.mp4", raw="A"),
        make_result(folder / "b.mp4", raw=None, error="boom"),
    ]

    runner = CliRunner()
    result = runner.invoke(video, ["transcribe", str(folder), "-f", "cfg.yaml"])

    assert result.exit_code == 1
    assert "✓ a.mp4" in result.output
    assert "✗ b.mp4: boom" in result.output
    # successful output still written
    legacy = wired["cfg"].paths.output_dir / "transcript.md"
    assert legacy.exists()
    assert "a.mp4:A" in legacy.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# pipeline: discovery + queue wiring
# --------------------------------------------------------------------------- #


def test_pipeline_default_recursive_workers_and_clean(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4", raw="RAW", cleaned="CLEAN")]

    runner = CliRunner()
    result = runner.invoke(video, ["pipeline", str(folder), "-f", "cfg.yaml"])

    assert result.exit_code == 0, result.output
    assert wired["recorded"]["recursive"] is True
    assert wired["recorded"]["max_workers"] == 2
    assert wired["recorded"]["skip_clean"] is False
    assert wired["recorded"]["cleaner_is_none"] is False
    assert "Queued 1 videos" in result.output

    scratch = wired["cfg"].paths.scratch_dir / "video" / folder.resolve().name
    raw = scratch / "transcript_raw.md"
    cleaned = scratch / "transcript_cleaned.md"
    assert raw.exists() and "a.mp4:RAW" in raw.read_text(encoding="utf-8")
    assert cleaned.exists() and "a.mp4:CLEAN" in cleaned.read_text(encoding="utf-8")
    # Cleaned came from the queue payload; no cleaner clean_file pass happened.


def test_pipeline_skip_clean(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4", raw="RAW")]

    runner = CliRunner()
    result = runner.invoke(
        video, ["pipeline", str(folder), "--skip-clean", "-f", "cfg.yaml"]
    )

    assert result.exit_code == 0, result.output
    assert wired["recorded"]["skip_clean"] is True
    assert wired["recorded"]["cleaner_is_none"] is True
    scratch = wired["cfg"].paths.scratch_dir / "video" / folder.resolve().name
    assert (scratch / "transcript_raw.md").exists()
    assert not (scratch / "transcript_cleaned.md").exists()


def test_pipeline_no_recursive_and_workers(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4", raw="RAW")]

    runner = CliRunner()
    result = runner.invoke(
        video,
        ["pipeline", str(folder), "--no-recursive", "--workers", "3", "-f", "cfg.yaml"],
    )

    assert result.exit_code == 0, result.output
    assert wired["recorded"]["recursive"] is False
    assert wired["recorded"]["max_workers"] == 3


def test_pipeline_nested_multi_job_per_parent(wired, tmp_path):
    root = tmp_path / "course"
    p1 = root / "L1"
    p2 = root / "L2"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)
    wired["files"] = [p1 / "a.mp4", p1 / "b.mp4", p2 / "c.mp4"]
    wired["results"] = [
        make_result(p1 / "a.mp4", raw="A"),
        make_result(p1 / "b.mp4", raw="B"),
        make_result(p2 / "c.mp4", raw="C"),
    ]

    runner = CliRunner()
    result = runner.invoke(
        video, ["pipeline", str(root), "--skip-clean", "-f", "cfg.yaml"]
    )

    assert result.exit_code == 0, result.output
    # Tree mode: per-parent scratch is the parent dir itself.
    raw1 = p1 / "transcript_raw.md"
    raw2 = p2 / "transcript_raw.md"
    assert raw1.exists() and raw2.exists()
    text1 = raw1.read_text(encoding="utf-8")
    assert "a.mp4:A" in text1 and "b.mp4:B" in text1
    assert "c.mp4:C" in raw2.read_text(encoding="utf-8")


def test_pipeline_partial_failure_exit_1_keeps_success(wired, tmp_path):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4", folder / "b.mp4"]
    wired["results"] = [
        make_result(folder / "a.mp4", raw="A"),
        make_result(folder / "b.mp4", raw=None, error="boom"),
    ]

    runner = CliRunner()
    result = runner.invoke(
        video, ["pipeline", str(folder), "--skip-clean", "-f", "cfg.yaml"]
    )

    assert result.exit_code == 1
    assert "✗ b.mp4: boom" in result.output
    scratch = wired["cfg"].paths.scratch_dir / "video" / folder.resolve().name
    raw = scratch / "transcript_raw.md"
    assert raw.exists() and "a.mp4:A" in raw.read_text(encoding="utf-8")


def test_pipeline_augment_serial_per_output(wired, tmp_path, monkeypatch):
    folder = tmp_path / "vids"
    folder.mkdir()
    wired["files"] = [folder / "a.mp4"]
    wired["results"] = [make_result(folder / "a.mp4", raw="RAW", cleaned="CLEAN")]

    calls = []

    class FakeAugmenter:
        def __init__(self, cfg):
            self.cfg = cfg

        def augment(self, current_file, final_path, auto_save=False):
            calls.append((Path(current_file), Path(final_path), auto_save))
            Path(final_path).parent.mkdir(parents=True, exist_ok=True)
            Path(final_path).write_text("final", encoding="utf-8")
            return Path(final_path)

    monkeypatch.setattr(video_cli, "TranscriptAugmenter", FakeAugmenter, raising=False)

    runner = CliRunner()
    result = runner.invoke(video, ["pipeline", str(folder), "--augment", "-f", "cfg.yaml"])

    assert result.exit_code == 0, result.output
    # One augment call, fed the cleaned file (queue payload).
    assert len(calls) == 1
    assert calls[0][0].name == "transcript_cleaned.md"
    assert calls[0][2] is False


# --------------------------------------------------------------------------- #
# Pre-existing command help / behaviour still intact
# --------------------------------------------------------------------------- #


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
