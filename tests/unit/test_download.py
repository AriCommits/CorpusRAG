"""Tests for video download (yt-dlp Python API)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.video.download import download_video, is_url


def test_is_url_https():
    assert is_url("https://youtube.com/watch?v=abc")


def test_is_url_http():
    assert is_url("http://example.com/video.mp4")


def test_is_url_www():
    assert is_url("www.youtube.com/watch?v=abc")


def test_is_url_local_path():
    assert not is_url("/home/user/video.mp4")
    assert not is_url("C:\\Users\\video.mp4")
    assert not is_url("./video.mp4")


class _FakeYDL:
    def __init__(self, opts, filename: Path, info: dict):
        self.opts = opts
        self._filename = str(filename)
        self._info = info

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        return self._info

    def prepare_filename(self, info):
        return self._filename


def test_download_video_success(tmp_path):
    dest = tmp_path / "test.mp4"
    dest.write_bytes(b"fake")
    info = {"title": "Test Video", "duration": 120, "ext": "mp4"}
    yt_dlp = MagicMock()
    yt_dlp.YoutubeDL.side_effect = lambda opts: _FakeYDL(opts, dest, info)

    with patch("tools.video.download._require_yt_dlp", return_value=yt_dlp):
        result = download_video("https://youtube.com/watch?v=abc", tmp_path)

    assert result.title == "Test Video"
    assert result.duration_sec == 120.0
    assert result.local_path == dest.resolve()
    opts = yt_dlp.YoutubeDL.call_args.args[0]
    assert opts["restrictfilenames"] is True
    assert opts["merge_output_format"] == "mp4"


def test_download_video_no_ytdlp(tmp_path):
    with patch(
        "tools.video.download._require_yt_dlp",
        side_effect=RuntimeError("yt-dlp is required for URL downloads"),
    ):
        with pytest.raises(RuntimeError, match="yt-dlp is required"):
            download_video("https://youtube.com/watch?v=abc", tmp_path)


def test_download_video_rejects_escape(tmp_path):
    outside = Path("/tmp/evil.mp4")
    info = {"title": "x", "duration": 1, "ext": "mp4"}
    yt_dlp = MagicMock()
    yt_dlp.YoutubeDL.side_effect = lambda opts: _FakeYDL(opts, outside, info)

    with patch("tools.video.download._require_yt_dlp", return_value=yt_dlp):
        with pytest.raises(RuntimeError, match="outside output directory"):
            download_video("https://youtube.com/watch?v=abc", tmp_path)


def test_validate_url_blocks_file_scheme():
    from tools.video.download import validate_video_url

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        validate_video_url("file:///etc/passwd")


def test_validate_url_blocks_private_ip():
    from tools.video.download import validate_video_url

    with pytest.raises(ValueError, match="Internal"):
        validate_video_url("http://169.254.169.254/latest/meta-data/")


def test_validate_url_blocks_localhost():
    from tools.video.download import validate_video_url

    with pytest.raises(ValueError, match="Internal"):
        validate_video_url("http://localhost:8080/secret")


def test_validate_url_allows_public():
    from tools.video.download import validate_video_url

    assert (
        validate_video_url("https://youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"
    )
