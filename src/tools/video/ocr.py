"""Vision OCR via Ollama multimodal models."""

import base64
import logging
from pathlib import Path

import httpx

from .classifier import FrameType

logger = logging.getLogger(__name__)

SLIDE_PROMPT = (
    "This is a frame from a lecture video showing a presentation slide. "
    "Transcribe ALL text visible on the slide exactly as written. "
    "Use # for slide titles, ## for section headers, bullets for body. "
    "Use LaTeX for math: inline $expr$, display $$expr$$. "
    "Do not describe images. If no readable text, respond: [NO_CONTENT]"
)

CHALKBOARD_PROMPT = (
    "This is a frame from a lecture video showing a chalkboard or whiteboard. "
    "Transcribe all visible text, equations, and diagrams. "
    "Use LaTeX for math: inline $expr$, display $$expr$$. "
    "For diagrams, use [Diagram: description]. "
    "If nothing instructional is visible, respond: [NO_CONTENT]"
)

_latex_model = None


def ocr_frame(
    frame_path: Path,
    frame_type: FrameType,
    model: str = "llava",
    endpoint: str = "http://localhost:11434",
) -> tuple[str, bool]:
    prompt = SLIDE_PROMPT if frame_type == FrameType.SLIDE else CHALKBOARD_PROMPT
    image_b64 = base64.b64encode(frame_path.read_bytes()).decode()

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{endpoint}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
                "stream": False,
            },
        )
        resp.raise_for_status()

    text = resp.json()["message"]["content"].strip()
    latex_chars = text.count("$") + text.count("\\")
    is_math_heavy = (latex_chars / max(len(text), 1)) > 0.25
    return text, is_math_heavy


def ocr_frame_latex(frame_path: Path) -> str:
    global _latex_model
    try:
        if _latex_model is None:
            from pix2tex.cli import LatexOCR
            _latex_model = LatexOCR()
        from PIL import Image
        img = Image.open(frame_path)
        latex = _latex_model(img)
        return f"$$\n{latex}\n$$"
    except Exception:
        return ""


def ocr_frame_with_fallback(
    frame_path: Path,
    frame_type: FrameType,
    model: str = "llava",
    endpoint: str = "http://localhost:11434",
    use_latex_fallback: bool = True,
) -> str:
    text, is_math_heavy = ocr_frame(frame_path, frame_type, model, endpoint)
    if text == "[NO_CONTENT]":
        return "[NO_CONTENT]"
    if (
        use_latex_fallback
        and is_math_heavy
        and frame_type in (FrameType.CHALKBOARD, FrameType.WHITEBOARD)
    ):
        latex_text = ocr_frame_latex(frame_path)
        if latex_text:
            return f"{text}\n\n{latex_text}"
    return text
