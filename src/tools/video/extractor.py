"""Keyframe extraction for video ingestion via PyAV (no ffmpeg binary)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFrame:
    path: Path
    frame_index: int
    source_timestamp_sec: float


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _validate_threshold(value: float) -> float:
    val = float(value)
    return max(0.0, min(1.0, val))


def _require_av():
    try:
        import av
    except ImportError as exc:
        raise RuntimeError(
            "PyAV is required for frame extraction. Install with: pip install corpusrag[video]"
        ) from exc
    return av


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    scene_threshold: float = 0.3,
    min_interval_sec: float = 2.0,
) -> list[ExtractedFrame]:
    """Extract scene-change keyframes with PyAV + Pillow.

    Consecutive RGB frames whose mean absolute difference (normalized to 0–1)
    meets ``scene_threshold`` are written as JPEGs, then filtered by
    ``min_interval_sec``.
    """
    import numpy as np
    from PIL import Image

    scene_threshold = _validate_threshold(scene_threshold)
    output_dir.mkdir(parents=True, exist_ok=True)

    av = _require_av()
    try:
        container = av.open(str(video_path))
    except Exception as exc:
        logger.debug("PyAV open failed: %s", exc)
        raise RuntimeError("frame extraction failed") from exc

    try:
        video_streams = getattr(container.streams, "video", None) or []
        stream = next(iter(video_streams), None)
        if stream is None:
            logger.warning("No video stream in %s", video_path)
            return []

        results: list[ExtractedFrame] = []
        prev = None
        last_ts = -min_interval_sec
        idx = 0

        for frame in container.decode(stream):
            ts = float(frame.time) if frame.time is not None else 0.0
            image = frame.to_ndarray(format="rgb24")
            if prev is not None:
                diff = float(np.mean(np.abs(image.astype("int16") - prev.astype("int16")))) / 255.0
                if diff < scene_threshold:
                    prev = image
                    continue
            if ts - last_ts < min_interval_sec:
                prev = image
                continue

            path = output_dir / f"frame_{idx + 1:06d}.jpg"
            Image.fromarray(image).save(path, quality=85)
            results.append(ExtractedFrame(path=path, frame_index=idx, source_timestamp_sec=ts))
            last_ts = ts
            idx += 1
            prev = image
    finally:
        container.close()

    if not results:
        logger.warning("No frames extracted from %s", video_path)
    return results
