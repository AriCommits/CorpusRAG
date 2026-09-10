"""FFmpeg-based audio extraction for video transcription."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_audio(
    video_path: Path,
    output_wav: Path,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    """Extract a mono PCM WAV audio track from ``video_path`` using ffmpeg.

    The audio is written to ``output_wav`` as 16-bit little-endian PCM at the
    requested ``sample_rate`` and ``channels``, which is the format Whisper and
    most speech models expect.

    Args:
        video_path: Source video file.
        output_wav: Destination ``.wav`` path. Parent directories are created.
        sample_rate: Output sample rate in Hz (default 16000).
        channels: Number of output audio channels (default 1, mono).

    Returns:
        The resolved path to the written WAV file.

    Raises:
        RuntimeError: If ffmpeg is not installed, or if it exits non-zero.
    """
    video = Path(video_path).resolve()
    wav = Path(output_wav).resolve()
    wav.parent.mkdir(parents=True, exist_ok=True)

    argv = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vn",
        "-map",
        "0:a:0",
        "-ac",
        str(int(channels)),
        "-ar",
        str(int(sample_rate)),
        "-c:a",
        "pcm_s16le",
        str(wav),
    ]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Install ffmpeg and ensure it is on your PATH.")

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        short = stderr[:500]
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}): {short}")

    return wav
