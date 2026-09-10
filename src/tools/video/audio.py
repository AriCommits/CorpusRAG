"""Audio extraction for video transcription via PyAV (no ffmpeg binary)."""

from __future__ import annotations

import logging
import wave
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_SAMPLE_RATE = 8000
MAX_SAMPLE_RATE = 48000
MIN_CHANNELS = 1
MAX_CHANNELS = 2
DEFAULT_TIMEOUT_SECONDS = 1800.0


def _clamp_int(value: object, lo: int, hi: int) -> int:
    return max(lo, min(int(value), hi))  # type: ignore[arg-type]


def _require_av():
    try:
        import av
    except ImportError as exc:
        raise RuntimeError(
            "PyAV is required for audio extraction. Install with: pip install corpusrag[video]"
        ) from exc
    return av


def extract_audio(
    video_path: Path,
    output_wav: Path,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
    allowed_root: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Path:
    """Extract a PCM WAV audio track from ``video_path`` using PyAV.

    The audio is written to ``output_wav`` as 16-bit little-endian PCM at the
    requested ``sample_rate`` and ``channels``, which is the format Whisper and
    most speech models expect. No ffmpeg/ffprobe binary on PATH is used.

    Args:
        video_path: Source video file.
        output_wav: Destination ``.wav`` path. Parent directories are created
            only after the path is confirmed to sit under ``allowed_root``.
        sample_rate: Output sample rate in Hz (clamped to 8000–48000).
        channels: Number of output audio channels (clamped to 1–2).
        allowed_root: Directory the WAV must remain inside. Defaults to the
            output file's parent.
        timeout: Decode deadline in seconds.

    Returns:
        The resolved path to the written WAV file.

    Raises:
        ValueError: If ``output_wav`` resolves outside ``allowed_root``.
        RuntimeError: If PyAV is missing, there is no audio stream, decode
            fails, or the timeout elapses.
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

    av = _require_av()

    def _run() -> None:
        _decode_to_wav(av, video, wav, sample_rate=sample_rate, channels=channels)

    if timeout is None or timeout <= 0:
        _run()
        return wav

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        try:
            future.result(timeout=timeout)
        except FuturesTimeout:
            raise RuntimeError("audio extraction timed out") from None

    return wav


def _decode_to_wav(av, video: Path, wav: Path, *, sample_rate: int, channels: int) -> None:
    import numpy as np

    try:
        container = av.open(str(video))
    except Exception as exc:
        logger.debug("PyAV open failed: %s", exc)
        raise RuntimeError("audio extraction failed") from exc

    try:
        audio_streams = getattr(container.streams, "audio", None) or []
        stream = next(iter(audio_streams), None)
        if stream is None:
            raise RuntimeError("no audio stream")

        layout = "mono" if channels == 1 else "stereo"
        resampler = av.AudioResampler(format="s16", layout=layout, rate=sample_rate)

        with wave.open(str(wav), "wb") as writer:
            writer.setnchannels(channels)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)

            def _write_frame(frame) -> None:
                array = frame.to_ndarray()
                if array.ndim == 2 and array.shape[0] == channels:
                    array = array.T.reshape(-1)
                writer.writeframes(np.ascontiguousarray(array, dtype="<i2").tobytes())

            try:
                for decoded in container.decode(stream):
                    resampled = resampler.resample(decoded)
                    if resampled is None:
                        continue
                    if not isinstance(resampled, (list, tuple)):
                        resampled = [resampled]
                    for piece in resampled:
                        _write_frame(piece)
                flushed = resampler.resample(None)
                if flushed:
                    if not isinstance(flushed, (list, tuple)):
                        flushed = [flushed]
                    for piece in flushed:
                        _write_frame(piece)
            except RuntimeError:
                raise
            except Exception as exc:
                logger.debug("PyAV decode failed: %s", exc)
                raise RuntimeError("audio extraction failed") from exc
    finally:
        container.close()
