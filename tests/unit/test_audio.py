"""Tests for video audio extraction."""

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
        result = extract_audio(Path("video.mp4"), out)

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


def test_extract_audio_no_binary(tmp_path):
    with patch("tools.video.audio.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav")


def test_extract_audio_failure(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "some ffmpeg error"

    with patch("tools.video.audio.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="ffmpeg failed"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav")


def test_extract_audio_custom_args(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    out = tmp_path / "out.wav"

    with patch("tools.video.audio.subprocess.run", return_value=mock_result) as run:
        extract_audio(Path("video.mp4"), out, sample_rate=44100, channels=2)

    argv = run.call_args.args[0]
    assert "-ac" in argv and argv[argv.index("-ac") + 1] == "2"
    assert "-ar" in argv and argv[argv.index("-ar") + 1] == "44100"
