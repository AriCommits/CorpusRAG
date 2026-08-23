"""Shared vision OCR client (Ollama /api/chat with a base64 image)."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx

MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB


def ocr_image(
    image_path: Path,
    prompt: str,
    *,
    model: str,
    endpoint: str = "http://localhost:11434",
    timeout: float = 120.0,
) -> str:
    """Run a vision model over an image and return stripped text.

    Oversized files return an empty string so callers can map that to their
    own skip sentinel (e.g. ``[NO_CONTENT]``).
    """
    if image_path.stat().st_size > MAX_IMAGE_SIZE:
        return ""

    image_b64 = base64.b64encode(image_path.read_bytes()).decode()
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{endpoint.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt, "images": [image_b64]},
                ],
                "stream": False,
            },
        )
        resp.raise_for_status()
    return resp.json()["message"]["content"].strip()
