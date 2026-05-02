"""Tests for video download."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.video.download import DownloadResult, download_video, is_url


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


def test_download_video_success(tmp_path):
    json_output = '{"_filename": "' + str(tmp_path / "test.mp4").replace("\\", "\\\\") + '", "title": "Test Video", "duration": 120}'
    mock_result = MagicMock()
    mock_result.stdout = json_output
    with patch("tools.video.download.subprocess.run", return_value=mock_result):
        result = download_video("https://youtube.com/watch?v=abc", tmp_path)
    assert result.title == "Test Video"
    assert result.duration_sec == 120.0


def test_download_video_no_ytdlp(tmp_path):
    with patch("tools.video.download.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="yt-dlp not found"):
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
    assert validate_video_url("https://youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"