"""Tests for vision OCR."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.video.classifier import FrameType
from tools.video.ocr import ocr_frame, ocr_frame_latex, ocr_frame_with_fallback


def _fake_frame(tmp_path: Path) -> Path:
    p = tmp_path / "frame.jpg"
    p.write_bytes(b"fakeimage")
    return p


def _mock_response(text: str):
    resp = MagicMock()
    resp.json.return_value = {"message": {"content": text}}
    resp.raise_for_status = MagicMock()
    return resp


def test_ocr_frame_slide(tmp_path):
    frame = _fake_frame(tmp_path)
    with patch("tools.video.ocr.httpx.Client") as mock_client:
        mock_client.return_value.__enter__ = lambda s: s
        mock_client.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.return_value.post.return_value = _mock_response("# Title\nBody text")
        text, is_math = ocr_frame(frame, FrameType.SLIDE)
    assert text == "# Title\nBody text"
    assert not is_math


def test_ocr_frame_math_heavy(tmp_path):
    frame = _fake_frame(tmp_path)
    # Dense LaTeX: many $ and \ chars relative to total length
    math_text = "$\\alpha$ $\\beta$ $\\gamma$ $\\delta$ $\\epsilon$"
    with patch("tools.video.ocr.httpx.Client") as mock_client:
        mock_client.return_value.__enter__ = lambda s: s
        mock_client.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.return_value.post.return_value = _mock_response(math_text)
        text, is_math = ocr_frame(frame, FrameType.CHALKBOARD)
    assert is_math


def test_ocr_frame_no_content(tmp_path):
    frame = _fake_frame(tmp_path)
    with patch("tools.video.ocr.httpx.Client") as mock_client:
        mock_client.return_value.__enter__ = lambda s: s
        mock_client.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.return_value.post.return_value = _mock_response("[NO_CONTENT]")
        result = ocr_frame_with_fallback(frame, FrameType.SLIDE)
    assert result == "[NO_CONTENT]"


def test_ocr_frame_latex_fallback_not_installed(tmp_path):
    frame = _fake_frame(tmp_path)
    result = ocr_frame_latex(frame)
    assert result == ""


def test_ocr_with_fallback_no_math(tmp_path):
    frame = _fake_frame(tmp_path)
    with patch("tools.video.ocr.httpx.Client") as mock_client:
        mock_client.return_value.__enter__ = lambda s: s
        mock_client.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.return_value.post.return_value = _mock_response("Regular slide text")
        result = ocr_frame_with_fallback(frame, FrameType.SLIDE)
    assert result == "Regular slide text"
