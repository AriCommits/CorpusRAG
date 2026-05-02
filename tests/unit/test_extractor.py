"""Tests for video frame extraction."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.video.extractor import ExtractedFrame, extract_keyframes, format_timestamp


def test_format_timestamp_zero():
    assert format_timestamp(0) == "00:00:00"


def test_format_timestamp_seconds():
    assert format_timestamp(45) == "00:00:45"


def test_format_timestamp_minutes():
    assert format_timestamp(125) == "00:02:05"


def test_format_timestamp_hours():
    assert format_timestamp(3661) == "01:01:01"


def test_extract_keyframes_no_ffmpeg():
    with patch("tools.video.extractor.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            extract_keyframes(Path("test.mp4"), Path("/tmp/out"))


def test_extract_keyframes_no_frames(tmp_path):
    with patch("tools.video.extractor.subprocess.run"):
        result = extract_keyframes(Path("test.mp4"), tmp_path)
        assert result == []


def test_extract_keyframes_with_frames(tmp_path):
    for i in range(3):
        (tmp_path / f"frame_{i+1:06d}.jpg").write_bytes(b"fake")

    mock_ffprobe = MagicMock()
    mock_ffprobe.stdout = "10.0\n20.0\n30.0\n"

    with patch("tools.video.extractor.subprocess.run", return_value=mock_ffprobe):
        result = extract_keyframes(Path("test.mp4"), tmp_path, min_interval_sec=2.0)

    assert len(result) == 3
    assert result[0].source_timestamp_sec == 10.0
    assert result[1].source_timestamp_sec == 20.0
    assert result[2].frame_index == 2


def test_extract_keyframes_min_interval_filter(tmp_path):
    for i in range(3):
        (tmp_path / f"frame_{i+1:06d}.jpg").write_bytes(b"fake")

    mock_ffprobe = MagicMock()
    mock_ffprobe.stdout = "10.0\n10.5\n20.0\n"

    with patch("tools.video.extractor.subprocess.run", return_value=mock_ffprobe):
        result = extract_keyframes(Path("test.mp4"), tmp_path, min_interval_sec=5.0)

    assert len(result) == 2
    assert result[0].source_timestamp_sec == 10.0
    assert result[1].source_timestamp_sec == 20.0



def test_threshold_validation_string():
    from tools.video.extractor import _validate_threshold
    assert _validate_threshold("0.5") == 0.5

def test_threshold_validation_clamp_high():
    from tools.video.extractor import _validate_threshold
    assert _validate_threshold(5.0) == 1.0

def test_threshold_validation_clamp_low():
    from tools.video.extractor import _validate_threshold
    assert _validate_threshold(-1.0) == 0.0