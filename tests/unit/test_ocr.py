"""Tests for vision OCR."""

from pathlib import Path
from unittest.mock import patch

from tools.video.classifier import FrameType
from tools.video.ocr import ocr_frame, ocr_frame_latex, ocr_frame_with_fallback


def _fake_frame(tmp_path: Path) -> Path:
    p = tmp_path / "frame.jpg"
    p.write_bytes(b"fakeimage")
    return p


def test_ocr_frame_slide(tmp_path):
    frame = _fake_frame(tmp_path)
    with patch("tools.video.ocr.ocr_image", return_value="# Title\nBody text"):
        text, is_math = ocr_frame(frame, FrameType.SLIDE)
    assert text == "# Title\nBody text"
    assert not is_math


def test_ocr_frame_math_heavy(tmp_path):
    frame = _fake_frame(tmp_path)
    math_text = "$\\alpha$ $\\beta$ $\\gamma$ $\\delta$ $\\epsilon$"
    with patch("tools.video.ocr.ocr_image", return_value=math_text):
        text, is_math = ocr_frame(frame, FrameType.CHALKBOARD)
    assert is_math


def test_ocr_frame_no_content(tmp_path):
    frame = _fake_frame(tmp_path)
    with patch("tools.video.ocr.ocr_image", return_value=""):
        result = ocr_frame_with_fallback(frame, FrameType.SLIDE)
    assert result == "[NO_CONTENT]"


def test_ocr_frame_latex_fallback_not_installed(tmp_path):
    frame = _fake_frame(tmp_path)
    result = ocr_frame_latex(frame)
    assert result == ""


def test_ocr_with_fallback_no_math(tmp_path):
    frame = _fake_frame(tmp_path)
    with patch("tools.video.ocr.ocr_image", return_value="Regular slide text"):
        result = ocr_frame_with_fallback(frame, FrameType.SLIDE)
    assert result == "Regular slide text"


def test_ocr_frame_skips_large_file(tmp_path):
    big_frame = tmp_path / "big.jpg"
    big_frame.write_bytes(b"x" * (51 * 1024 * 1024))  # 51MB
    text, is_math = ocr_frame(big_frame, FrameType.SLIDE)
    assert text == "[NO_CONTENT]"
    assert not is_math
