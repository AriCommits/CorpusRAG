"""Heuristic frame classifier for video content."""

from enum import Enum
from pathlib import Path

import numpy as np
from PIL import Image


class FrameType(Enum):
    SLIDE = "slide"
    CHALKBOARD = "chalkboard"
    WHITEBOARD = "whiteboard"
    NO_CONTENT = "no_content"


def classify_frame(frame_path: Path) -> FrameType:
    img = Image.open(frame_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    mean_brightness = arr.mean()

    if mean_brightness < 60:
        return FrameType.CHALKBOARD

    if mean_brightness > 180:
        std = arr.std()
        if std > 40:
            return FrameType.SLIDE
        return FrameType.NO_CONTENT

    edges = _edge_density(arr)
    if edges > 0.05:
        return FrameType.WHITEBOARD
    return FrameType.NO_CONTENT


def _edge_density(arr: np.ndarray) -> float:
    gray = arr.mean(axis=2)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    return float((gx + gy) / 2 / 255)
