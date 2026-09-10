"""Video download via the yt-dlp Python API (no yt-dlp binary)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    local_path: Path
    title: str
    duration_sec: float
    url: str


def is_url(path_or_url: str) -> bool:
    return path_or_url.startswith(("http://", "https://", "www."))


def validate_video_url(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    hostname = (parsed.hostname or "").lower()
    _blocked = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")
    if hostname in _blocked or hostname.startswith(("10.", "192.168.", "169.254.")):
        raise ValueError(f"Internal/private URLs not allowed: {hostname}")
    if hostname.startswith("172."):
        parts = hostname.split(".")
        if len(parts) >= 2 and 16 <= int(parts[1]) <= 31:
            raise ValueError(f"Internal/private URLs not allowed: {hostname}")
    return url


def _require_yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is required for URL downloads. Install with: pip install corpusrag[video]"
        ) from exc
    return yt_dlp


def download_video(url: str, output_dir: Path) -> DownloadResult:
    url = validate_video_url(url)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    yt_dlp = _require_yt_dlp()
    outtmpl = str(output_dir / "%(title)s.%(ext)s")
    options = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "restrictfilenames": True,
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
    except RuntimeError:
        raise
    except Exception as exc:
        logger.debug("yt-dlp failed: %s", exc)
        raise RuntimeError("yt-dlp failed") from exc

    if info.get("ext"):
        merged = Path(filepath).with_suffix(".mp4")
        if merged.exists():
            filepath = str(merged)

    resolved = Path(filepath).resolve()
    if not resolved.is_relative_to(output_dir.resolve()):
        raise RuntimeError("Downloaded file outside output directory")

    return DownloadResult(
        local_path=resolved,
        title=info.get("title", "Unknown"),
        duration_sec=float(info.get("duration") or 0),
        url=url,
    )
