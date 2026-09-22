"""Tests for VideoTranscriber audio-extraction transcription path.

These tests mock ``extract_audio`` and ``_load_model`` so no ffmpeg or Whisper
model is required. They verify that Whisper is invoked on the extracted WAV
(not the source video), that the extraction receives the configured sample
rate/channels, and that the scratch WAV is cleaned up unless
``keep_extracted_audio`` is set.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.video.config import VideoConfig
from tools.video.transcribe import VideoTranscriber


def _make_config(tmp_path: Path, **video_overrides) -> VideoConfig:
    data = {
        "llm": {},
        "embedding": {},
        "database": {},
        "paths": {"scratch_dir": str(tmp_path / "scratch")},
        "video": video_overrides,
    }
    return VideoConfig.from_dict(data)


def _make_segment(text, start=0.0, end=1.0):
    seg = MagicMock()
    seg.text = text
    seg.start = start
    seg.end = end
    return seg


def _patch_transcriber(transcriber, segments):
    """Patch _load_model to return a mock whisper model yielding ``segments``."""
    model = MagicMock()
    model.transcribe.return_value = (iter(segments), MagicMock())
    return patch.object(transcriber, "_load_model", return_value=model), model


def test_transcribes_wav_not_video(tmp_path):
    cfg = _make_config(tmp_path)
    transcriber = VideoTranscriber(cfg)
    model_patch, model = _patch_transcriber(transcriber, [_make_segment("hello world")])

    video = tmp_path / "lecture.mp4"

    with model_patch, patch("tools.video.transcribe.audio.extract_audio") as extract:
        result = transcriber.transcribe_file(video)

    assert result == "hello world"

    # extract_audio called with configured sample rate / channels
    assert extract.call_count == 1
    call = extract.call_args
    assert call.args[0] == video
    wav_arg = Path(call.args[1])
    assert wav_arg.suffix == ".wav"
    assert wav_arg.stem.startswith("lecture_")
    assert wav_arg.parent == cfg.paths.scratch_dir / "audio"
    assert call.kwargs["sample_rate"] == 16000
    assert call.kwargs["channels"] == 1
    assert call.kwargs["allowed_root"] == (cfg.paths.scratch_dir / "audio").resolve()

    # Whisper ran on the WAV, not the MP4
    assert model.transcribe.call_count == 1
    transcribe_arg = model.transcribe.call_args.args[0]
    assert transcribe_arg.endswith(".wav")
    assert not transcribe_arg.endswith(".mp4")


def test_uses_custom_audio_settings(tmp_path):
    cfg = _make_config(tmp_path, audio_sample_rate=44100, audio_channels=2)
    transcriber = VideoTranscriber(cfg)
    model_patch, _ = _patch_transcriber(transcriber, [_make_segment("hi")])

    with model_patch, patch("tools.video.transcribe.audio.extract_audio") as extract:
        transcriber.transcribe_file(tmp_path / "clip.mkv")

    assert extract.call_args.kwargs["sample_rate"] == 44100
    assert extract.call_args.kwargs["channels"] == 2


def test_cleans_up_wav_by_default(tmp_path):
    cfg = _make_config(tmp_path)
    transcriber = VideoTranscriber(cfg)
    model_patch, _ = _patch_transcriber(transcriber, [_make_segment("text")])

    created = {}

    def fake_extract(video_path, output_wav, **kwargs):
        wav = Path(output_wav)
        wav.parent.mkdir(parents=True, exist_ok=True)
        wav.write_bytes(b"RIFF")
        created["wav"] = wav
        return wav

    with model_patch, patch("tools.video.transcribe.audio.extract_audio", side_effect=fake_extract):
        transcriber.transcribe_file(tmp_path / "lecture.mp4")

    assert not created["wav"].exists()


def test_keeps_wav_when_configured(tmp_path):
    cfg = _make_config(tmp_path, keep_extracted_audio=True)
    transcriber = VideoTranscriber(cfg)
    model_patch, _ = _patch_transcriber(transcriber, [_make_segment("text")])

    created = {}

    def fake_extract(video_path, output_wav, **kwargs):
        wav = Path(output_wav)
        wav.parent.mkdir(parents=True, exist_ok=True)
        wav.write_bytes(b"RIFF")
        created["wav"] = wav
        return wav

    with model_patch, patch("tools.video.transcribe.audio.extract_audio", side_effect=fake_extract):
        transcriber.transcribe_file(tmp_path / "lecture.mp4")

    assert created["wav"].exists()


def test_cleans_up_wav_on_transcribe_error(tmp_path):
    cfg = _make_config(tmp_path)
    transcriber = VideoTranscriber(cfg)

    model = MagicMock()
    model.transcribe.side_effect = RuntimeError("whisper boom")

    created = {}

    def fake_extract(video_path, output_wav, **kwargs):
        wav = Path(output_wav)
        wav.parent.mkdir(parents=True, exist_ok=True)
        wav.write_bytes(b"RIFF")
        created["wav"] = wav
        return wav

    with (
        patch.object(transcriber, "_load_model", return_value=model),
        patch("tools.video.transcribe.audio.extract_audio", side_effect=fake_extract),
    ):
        try:
            transcriber.transcribe_file(tmp_path / "lecture.mp4")
        except RuntimeError:
            pass

    assert not created["wav"].exists()


def test_timestamps_formatting_preserved(tmp_path):
    cfg = _make_config(tmp_path, include_timestamps=True)
    transcriber = VideoTranscriber(cfg)
    segments = [
        _make_segment("first", start=0.0, end=1.5),
        _make_segment("second", start=1.5, end=3.0),
    ]
    model_patch, _ = _patch_transcriber(transcriber, segments)

    with model_patch, patch("tools.video.transcribe.audio.extract_audio"):
        result = transcriber.transcribe_file(tmp_path / "lecture.mp4")

    assert result == "[0.00s - 1.50s] first\n[1.50s - 3.00s] second"


def test_load_model_is_serialized_across_workers(tmp_path):
    import threading
    import time

    cfg = _make_config(tmp_path)
    transcriber = VideoTranscriber(cfg)

    current = 0
    max_current = 0
    counter_lock = threading.Lock()
    model = MagicMock()
    model.transcribe.return_value = (iter([]), MagicMock())

    def slow_load():
        nonlocal current, max_current
        with counter_lock:
            current += 1
            max_current = max(max_current, current)
        time.sleep(0.08)
        with counter_lock:
            current -= 1
        return model

    transcriber._load_model = slow_load  # type: ignore[method-assign]

    def fake_extract(video_path, output_wav, **kwargs):
        return Path(output_wav)

    errors: list[BaseException] = []

    def worker(name: str) -> None:
        try:
            with patch("tools.video.transcribe.audio.extract_audio", side_effect=fake_extract):
                transcriber.transcribe_file(tmp_path / f"{name}.mp4")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("a",)),
        threading.Thread(target=worker, args=("b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert max_current == 1
