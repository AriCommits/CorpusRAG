"""Tests for frame classification."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools.video.classifier import FrameType, classify_frame


def _make_image(tmp_path: Path, name: str, color: tuple, noise: bool = False) -> Path:
    img = Image.new("RGB", (100, 100), color)
    if noise:
        arr = np.array(img)
        rng = np.random.default_rng(42)
        arr = np.clip(arr.astype(np.int16) + rng.integers(-80, 80, arr.shape), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
    path = tmp_path / name
    img.save(path)
    return path


def _make_edge_image(tmp_path: Path, name: str) -> Path:
    arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    for i in range(0, 100, 5):
        arr[i, :, :] = 0
        arr[:, i, :] = 0
    img = Image.fromarray(arr)
    path = tmp_path / name
    img.save(path)
    return path


def test_chalkboard_dark(tmp_path):
    path = _make_image(tmp_path, "dark.jpg", (20, 20, 20))
    assert classify_frame(path) == FrameType.CHALKBOARD


def test_slide_bright_high_contrast(tmp_path):
    # White background with black "text" lines = high mean brightness + high std
    arr = np.full((100, 100, 3), 240, dtype=np.uint8)
    arr[10:15, :, :] = 0  # black horizontal lines
    arr[30:35, :, :] = 0
    arr[50:55, :, :] = 0
    img = Image.fromarray(arr)
    path = tmp_path / "slide.jpg"
    img.save(path)
    assert classify_frame(path) == FrameType.SLIDE


def test_no_content_bright_uniform(tmp_path):
    path = _make_image(tmp_path, "blank.jpg", (240, 240, 240))
    assert classify_frame(path) == FrameType.NO_CONTENT


def test_whiteboard_mid_with_edges(tmp_path):
    path = _make_edge_image(tmp_path, "wb.jpg")
    assert classify_frame(path) == FrameType.WHITEBOARD


def test_no_content_mid_no_edges(tmp_path):
    path = _make_image(tmp_path, "gray.jpg", (128, 128, 128))
    assert classify_frame(path) == FrameType.NO_CONTENT
