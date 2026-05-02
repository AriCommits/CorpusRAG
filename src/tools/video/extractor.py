"""FFmpeg-based keyframe extraction for video ingestion."""

import logging
import subprocess
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


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    scene_threshold: float = 0.3,
    min_interval_sec: float = 2.0,
) -> list[ExtractedFrame]:
    scene_threshold = _validate_threshold(scene_threshold)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%06d.jpg")

    try:
        subprocess.run(
            [
                "ffmpeg", "-i", str(video_path),
                "-vf", f"select=gt(scene\\,{scene_threshold}),setpts=N/FRAME_RATE/TB",
                "-vsync", "vfr",
                "-frame_pts", "1",
                output_pattern,
            ],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install ffmpeg and ensure it is on your PATH."
        )

    frame_paths = sorted(output_dir.glob("frame_*.jpg"))
    if not frame_paths:
        logger.warning("No frames extracted from %s", video_path)
        return []

    timestamps = _get_timestamps(video_path, len(frame_paths))

    # Apply min_interval filter
    results = []
    last_ts = -min_interval_sec
    idx = 0
    for path, ts in zip(frame_paths, timestamps):
        if ts - last_ts >= min_interval_sec:
            results.append(ExtractedFrame(path=path, frame_index=idx, source_timestamp_sec=ts))
            last_ts = ts
            idx += 1
        else:
            path.unlink(missing_ok=True)

    return results


def _get_timestamps(video_path: Path, n_frames: int) -> list[float]:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v",
                "-show_entries", "frame=pts_time",
                "-of", "csv=p=0",
                str(video_path),
            ],
            capture_output=True, text=True,
        )
        times = []
        for line in result.stdout.strip().splitlines():
            try:
                times.append(float(line.strip()))
            except ValueError:
                continue
        if len(times) >= n_frames:
            return times[:n_frames]
    except FileNotFoundError:
        pass
    return [i * 5.0 for i in range(n_frames)]
