"""Tests for video OCR pipeline orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.video.classifier import FrameType
from tools.video.extractor import ExtractedFrame
from tools.video.ingest import VideoIngestResult, ingest_video
from tools.video.config import VideoConfig


def _make_config() -> VideoConfig:
    return VideoConfig.from_dict({
        "llm": {"endpoint": "http://localhost:11434"},
        "embedding": {},
        "database": {},
        "paths": {"scratch_dir": "./scratch"},
        "video": {"vision_model": "llava", "scene_threshold": 0.3},
    })


def _fake_frames(n: int) -> list[ExtractedFrame]:
    return [
        ExtractedFrame(path=Path(f"frame_{i}.jpg"), frame_index=i, source_timestamp_sec=i * 10.0)
        for i in range(n)
    ]


@patch("tools.video.ingest.extract_keyframes")
@patch("tools.video.ingest.classify_frame")
@patch("tools.video.ingest.ocr_frame_with_fallback")
def test_full_pipeline(mock_ocr, mock_classify, mock_extract):
    mock_extract.return_value = _fake_frames(3)
    mock_classify.return_value = FrameType.SLIDE
    mock_ocr.return_value = "# Slide content"

    cfg = _make_config()
    result = ingest_video(Path("test.mp4"), cfg)

    assert isinstance(result, VideoIngestResult)
    assert result.frames_extracted == 3
    assert result.chunks_after_dedup >= 1
    assert result.source_file == "test.mp4"


@patch("tools.video.ingest.extract_keyframes")
def test_no_frames(mock_extract):
    mock_extract.return_value = []
    cfg = _make_config()
    result = ingest_video(Path("empty.mp4"), cfg)
    assert result.frames_extracted == 0
    assert result.chunks_after_dedup == 0


@patch("tools.video.ingest.extract_keyframes")
@patch("tools.video.ingest.classify_frame")
def test_all_no_content(mock_classify, mock_extract):
    mock_extract.return_value = _fake_frames(3)
    mock_classify.return_value = FrameType.NO_CONTENT

    cfg = _make_config()
    result = ingest_video(Path("boring.mp4"), cfg)
    assert result.frames_skipped == 3
    assert result.chunks_after_dedup == 0


@patch("tools.video.ingest.extract_keyframes")
@patch("tools.video.ingest.classify_frame")
@patch("tools.video.ingest.ocr_frame_with_fallback")
def test_progress_callback(mock_ocr, mock_classify, mock_extract):
    mock_extract.return_value = _fake_frames(2)
    mock_classify.return_value = FrameType.SLIDE
    mock_ocr.return_value = "content"

    progress_calls = []
    def cb(pct, step):
        progress_calls.append((pct, step))

    cfg = _make_config()
    ingest_video(Path("test.mp4"), cfg, progress_cb=cb)

    # Should have progress calls from 0 to 100
    assert len(progress_calls) > 0
    assert progress_calls[0][0] == 0
    assert progress_calls[-1][0] == 100


@patch("tools.video.ingest.extract_keyframes")
@patch("tools.video.ingest.classify_frame")
@patch("tools.video.ingest.ocr_frame_with_fallback")
def test_output_file(mock_ocr, mock_classify, mock_extract, tmp_path):
    mock_extract.return_value = _fake_frames(2)
    mock_classify.return_value = FrameType.SLIDE
    mock_ocr.return_value = "# Title"

    cfg = _make_config()
    result = ingest_video(Path("lecture.mp4"), cfg, output_dir=tmp_path)

    assert result.output_path is not None
    assert result.output_path.exists()
    content = result.output_path.read_text()
    assert "# Title" in content


@patch("tools.video.ingest.extract_keyframes")
@patch("tools.video.ingest.classify_frame")
@patch("tools.video.ingest.ocr_frame_with_fallback")
def test_config_overrides(mock_ocr, mock_classify, mock_extract):
    mock_extract.return_value = _fake_frames(1)
    mock_classify.return_value = FrameType.SLIDE
    mock_ocr.return_value = "text"

    cfg = _make_config()
    ingest_video(
        Path("test.mp4"), cfg,
        scene_threshold=0.5, vision_model="moondream",
    )

    # Verify extract was called with overridden threshold
    mock_extract.assert_called_once()
    call_args = mock_extract.call_args
    assert call_args[0][2] == 0.5  # scene_threshold

    # Verify OCR was called with overridden model
    mock_ocr.assert_called_once()
    assert mock_ocr.call_args[1]["model"] == "moondream"
