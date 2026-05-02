"""Video download via yt-dlp."""

import json
import logging
import subprocess
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


def download_video(url: str, output_dir: Path) -> DownloadResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", str(output_dir / "%(title)s.%(ext)s"),
                "--print-json",
                "--no-simulate",
                "--restrict-filenames",
                url,
            ],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp not found. Install with: pip install yt-dlp (or system package manager)"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"yt-dlp failed: {e.stderr}")

    # yt-dlp --print-json outputs one JSON object per line
    for line in result.stdout.strip().splitlines():
        try:
            info = json.loads(line)
            filepath = info.get("_filename") or info.get("filename", "")
            resolved = Path(filepath).resolve()
            if not resolved.is_relative_to(output_dir.resolve()):
                raise RuntimeError(f"Downloaded file outside output directory")
            return DownloadResult(
                local_path=Path(filepath),
                title=info.get("title", "Unknown"),
                duration_sec=float(info.get("duration", 0)),
                url=url,
            )
        except json.JSONDecodeError:
            continue

    raise RuntimeError("Failed to parse yt-dlp output")
