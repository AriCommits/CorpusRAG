"""Vision OCR pass for handwritten documents."""

import base64
from pathlib import Path

import ollama

HANDWRITING_PROMPT = """
You are transcribing a handwritten document page to markdown.

Instructions:
- Transcribe ALL visible handwritten text as accurately as possible
- Preserve the logical structure: use # for titles, ## for section headers,
  bullet points for lists, and paragraphs for flowing notes
- For mathematical or technical notation, use LaTeX: inline as $expr$,
  display equations as $$expr$$
- For diagrams, sketches, or drawings: describe them concisely in square
  brackets, e.g. [Diagram: circuit with resistor R1 connected to voltage source]
- For crossed-out text: use ~~strikethrough~~ markdown
- For arrows or connective annotations: describe the relationship in brackets,
  e.g. [Arrow from step 3 pointing to note in margin]
- If a word or phrase is genuinely illegible (not just hard to read),
  mark it as [illegible]
- If the page is blank or contains only doodles with no text, respond
  with exactly: [BLANK_PAGE]
- Do not add any commentary, explanation, or preamble — output only the
  transcribed markdown
"""


def ocr_handwriting(
    image_path: Path,
    model: str = "llava",
) -> str:
    """
    Run handwriting OCR on a single image using a vision model.
    Returns raw transcribed markdown.

    Args:
        image_path: Path to the image file to OCR.
        model: Ollama model to use (default: "llava").

    Returns:
        Raw transcribed markdown as a string.
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    response = ollama.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": HANDWRITING_PROMPT,
            "images": [image_b64],
        }]
    )
    return response["message"]["content"].strip()
