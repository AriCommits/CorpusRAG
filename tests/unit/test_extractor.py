"""Tests for video frame extraction (PyAV)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tools.video.extractor import extract_keyframes, format_timestamp


def test_format_timestamp_zero():
    assert format_timestamp(0) == "00:00:00"


def test_format_timestamp_seconds():
    assert format_timestamp(45) == "00:00:45"


def test_format_timestamp_minutes():
    assert format_timestamp(125) == "00:02:05"


def test_format_timestamp_hours():
    assert format_timestamp(3661) == "01:01:01"


class _FakeFrame:
    def __init__(self, time: float, fill: int):
        self.time = time
        self._fill = fill

    def to_ndarray(self, format="rgb24"):
        return np.full((4, 4, 3), self._fill, dtype=np.uint8)


class _FakeContainer:
    def __init__(self, frames, has_video=True):
        self.streams = MagicMock()
        self.streams.video = [object()] if has_video else []
        self._frames = frames
        self.closed = False

    def decode(self, stream):
        return iter(self._frames)

    def close(self):
        self.closed = True


def test_extract_keyframes_no_pyav(tmp_path):
    with patch(
        "tools.video.extractor._require_av",
        side_effect=RuntimeError("PyAV is required for frame extraction"),
    ):
        with pytest.raises(RuntimeError, match="PyAV is required"):
            extract_keyframes(Path("test.mp4"), tmp_path)


def test_extract_keyframes_no_frames(tmp_path):
    av = MagicMock()
    av.open.return_value = _FakeContainer([], has_video=True)
    with patch("tools.video.extractor._require_av", return_value=av):
        result = extract_keyframes(Path("test.mp4"), tmp_path)
    assert result == []


def test_extract_keyframes_with_frames(tmp_path):
    frames = [
        _FakeFrame(10.0, 0),
        _FakeFrame(20.0, 255),
        _FakeFrame(30.0, 0),
    ]
    av = MagicMock()
    av.open.return_value = _FakeContainer(frames)
    with patch("tools.video.extractor._require_av", return_value=av):
        result = extract_keyframes(Path("test.mp4"), tmp_path, min_interval_sec=2.0)

    assert len(result) == 3
    assert result[0].source_timestamp_sec == 10.0
    assert result[1].source_timestamp_sec == 20.0
    assert result[2].frame_index == 2
    assert (tmp_path / "frame_000001.jpg").exists()


def test_extract_keyframes_min_interval_filter(tmp_path):
    frames = [
        _FakeFrame(10.0, 0),
        _FakeFrame(10.5, 255),
        _FakeFrame(20.0, 0),
    ]
    av = MagicMock()
    av.open.return_value = _FakeContainer(frames)
    with patch("tools.video.extractor._require_av", return_value=av):
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
