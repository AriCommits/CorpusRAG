"""Tests for video audio extraction."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.video.audio import extract_audio


def test_extract_audio_happy(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    out = tmp_path / "nested" / "out.wav"

    with patch("tools.video.audio.subprocess.run", return_value=mock_result) as run:
        result = extract_audio(Path("video.mp4"), out, allowed_root=tmp_path)

    assert result == out.resolve()
    assert out.parent.exists()

    argv = run.call_args.args[0]
    video = str(Path("video.mp4").resolve())
    wav = str(out.resolve())
    assert argv == [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video,
        "-vn",
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        wav,
    ]
    assert run.call_args.kwargs["timeout"] == 1800.0


def test_extract_audio_no_binary(tmp_path):
    with patch("tools.video.audio.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)


def test_extract_audio_failure_hides_stderr(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "C:\\secret\\path failed"

    with patch("tools.video.audio.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match=r"ffmpeg failed \(exit 1\)") as exc:
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)

    assert "secret" not in str(exc.value)


def test_extract_audio_timeout(tmp_path):
    with patch(
        "tools.video.audio.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1),
    ):
        with pytest.raises(RuntimeError, match="ffmpeg timed out"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)


def test_extract_audio_custom_args(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    out = tmp_path / "out.wav"

    with patch("tools.video.audio.subprocess.run", return_value=mock_result) as run:
        extract_audio(
            Path("video.mp4"),
            out,
            sample_rate=44100,
            channels=2,
            allowed_root=tmp_path,
        )

    argv = run.call_args.args[0]
    assert "-ac" in argv and argv[argv.index("-ac") + 1] == "2"
    assert "-ar" in argv and argv[argv.index("-ar") + 1] == "44100"


def test_extract_audio_clamps_rate_and_channels(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    out = tmp_path / "out.wav"

    with patch("tools.video.audio.subprocess.run", return_value=mock_result) as run:
        extract_audio(
            Path("video.mp4"),
            out,
            sample_rate=99_999_999,
            channels=64,
            allowed_root=tmp_path,
        )

    argv = run.call_args.args[0]
    assert argv[argv.index("-ac") + 1] == "2"
    assert argv[argv.index("-ar") + 1] == "48000"


def test_extract_audio_rejects_escape(tmp_path):
    allowed = tmp_path / "audio"
    allowed.mkdir()
    outside = tmp_path / "other" / "evil.wav"

    with pytest.raises(ValueError, match="escapes allowed root"):
        extract_audio(Path("video.mp4"), outside, allowed_root=allowed)
