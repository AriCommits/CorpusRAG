"""Vision OCR pass for handwritten documents."""

from pathlib import Path

from tools.ocr_client import ocr_image

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
    return ocr_image(image_path, HANDWRITING_PROMPT, model=model)
