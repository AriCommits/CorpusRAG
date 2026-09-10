"""FFmpeg-based audio extraction for video transcription."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_SAMPLE_RATE = 8000
MAX_SAMPLE_RATE = 48000
MIN_CHANNELS = 1
MAX_CHANNELS = 2
DEFAULT_TIMEOUT_SECONDS = 1800.0


def _clamp_int(value: object, lo: int, hi: int) -> int:
    return max(lo, min(int(value), hi))  # type: ignore[arg-type]


def extract_audio(
    video_path: Path,
    output_wav: Path,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
    allowed_root: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Path:
    """Extract a mono PCM WAV audio track from ``video_path`` using ffmpeg.

    The audio is written to ``output_wav`` as 16-bit little-endian PCM at the
    requested ``sample_rate`` and ``channels``, which is the format Whisper and
    most speech models expect.

    Args:
        video_path: Source video file.
        output_wav: Destination ``.wav`` path. Parent directories are created
            only after the path is confirmed to sit under ``allowed_root``.
        sample_rate: Output sample rate in Hz (clamped to 8000–48000).
        channels: Number of output audio channels (clamped to 1–2).
        allowed_root: Directory the WAV must remain inside. Defaults to the
            output file's parent.
        timeout: ffmpeg kill deadline in seconds.

    Returns:
        The resolved path to the written WAV file.

    Raises:
        ValueError: If ``output_wav`` resolves outside ``allowed_root``.
        RuntimeError: If ffmpeg is not installed, times out, or exits non-zero.
    """
    video = Path(video_path).resolve()
    wav = Path(output_wav).resolve()
    root = Path(allowed_root).resolve() if allowed_root is not None else wav.parent
    try:
        wav.relative_to(root)
    except ValueError:
        raise ValueError(f"audio output escapes allowed root: {wav} (root {root})") from None

    sample_rate = _clamp_int(sample_rate, MIN_SAMPLE_RATE, MAX_SAMPLE_RATE)
    channels = _clamp_int(channels, MIN_CHANNELS, MAX_CHANNELS)

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
        str(channels),
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(wav),
    ]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Install ffmpeg and ensure it is on your PATH.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg timed out")

    if result.returncode != 0:
        logger.debug("ffmpeg stderr: %s", (result.stderr or "").strip())
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode})")

    return wav
