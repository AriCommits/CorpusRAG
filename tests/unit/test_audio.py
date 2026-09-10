"""Tests for video audio extraction (PyAV)."""

from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tools.video.audio import extract_audio


def _pcm_frame(channels: int = 1, samples: int = 4):
    frame = MagicMock()
    if channels == 1:
        frame.to_ndarray.return_value = np.zeros(samples, dtype=np.int16)
    else:
        frame.to_ndarray.return_value = np.zeros((channels, samples), dtype=np.int16)
    return frame


def _fake_av(frames=None):
    av = MagicMock()
    container = MagicMock()
    stream = object()
    container.streams.audio = [stream]
    container.decode.return_value = list(frames or [_pcm_frame()])
    av.open.return_value = container
    resampler = MagicMock()
    resampler.resample.side_effect = lambda frame: [] if frame is None else [frame]
    av.AudioResampler.return_value = resampler
    return av, container


def test_extract_audio_happy(tmp_path):
    out = tmp_path / "nested" / "out.wav"
    av, container = _fake_av()

    with patch("tools.video.audio._require_av", return_value=av):
        result = extract_audio(Path("video.mp4"), out, allowed_root=tmp_path)

    assert result == out.resolve()
    assert out.exists()
    av.open.assert_called_once_with(str(Path("video.mp4").resolve()))
    av.AudioResampler.assert_called_once_with(format="s16", layout="mono", rate=16000)
    container.close.assert_called()


def test_extract_audio_missing_pyav(tmp_path):
    with patch(
        "tools.video.audio._require_av",
        side_effect=RuntimeError("PyAV is required for audio extraction"),
    ):
        with pytest.raises(RuntimeError, match="PyAV is required"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)


def test_extract_audio_no_audio_stream(tmp_path):
    av, container = _fake_av()
    container.streams.audio = []

    with patch("tools.video.audio._require_av", return_value=av):
        with pytest.raises(RuntimeError, match="no audio stream"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)


def test_extract_audio_open_failure_hides_details(tmp_path):
    av = MagicMock()
    av.open.side_effect = OSError("C:\\secret\\path failed")

    with patch("tools.video.audio._require_av", return_value=av):
        with pytest.raises(RuntimeError, match="audio extraction failed") as exc:
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)

    assert "secret" not in str(exc.value)


def test_extract_audio_timeout(tmp_path):
    av, _container = _fake_av()
    future = MagicMock()
    future.result.side_effect = FuturesTimeout()
    pool = MagicMock()
    pool.__enter__.return_value = pool
    pool.__exit__.return_value = False
    pool.submit.return_value = future

    with (
        patch("tools.video.audio._require_av", return_value=av),
        patch("tools.video.audio.ThreadPoolExecutor", return_value=pool),
    ):
        with pytest.raises(RuntimeError, match="audio extraction timed out"):
            extract_audio(Path("video.mp4"), tmp_path / "out.wav", allowed_root=tmp_path)


def test_extract_audio_custom_rate_and_channels(tmp_path):
    out = tmp_path / "out.wav"
    av, _container = _fake_av(frames=[_pcm_frame(channels=2)])

    with patch("tools.video.audio._require_av", return_value=av):
        extract_audio(
            Path("video.mp4"),
            out,
            sample_rate=44100,
            channels=2,
            allowed_root=tmp_path,
        )

    av.AudioResampler.assert_called_once_with(format="s16", layout="stereo", rate=44100)


def test_extract_audio_clamps_rate_and_channels(tmp_path):
    out = tmp_path / "out.wav"
    av, _container = _fake_av(frames=[_pcm_frame(channels=2)])

    with patch("tools.video.audio._require_av", return_value=av):
        extract_audio(
            Path("video.mp4"),
            out,
            sample_rate=99_999_999,
            channels=64,
            allowed_root=tmp_path,
        )

    av.AudioResampler.assert_called_once_with(format="s16", layout="stereo", rate=48000)


def test_extract_audio_rejects_escape(tmp_path):
    allowed = tmp_path / "audio"
    allowed.mkdir()
    outside = tmp_path / "other" / "evil.wav"

    with pytest.raises(ValueError, match="escapes allowed root"):
        extract_audio(Path("video.mp4"), outside, allowed_root=allowed)
