"""LLM correction pass for OCR output."""

import ollama

CORRECTION_PROMPT = """
You are correcting handwritten notes that were transcribed by a vision model.
The transcription may contain OCR errors: misread characters, spelling mistakes,
incorrect word boundaries, or garbled technical terms.

Your task:
1. Fix obvious OCR errors and misspellings caused by misread handwriting
2. Preserve intentional abbreviations (e.g. "eq." for equation, "cf." for compare)
3. Preserve domain-specific terminology even if it looks unusual
4. Preserve ALL [illegible] markers — do not guess at illegible content
5. Preserve ALL [Diagram: ...] descriptions unchanged
6. Preserve ALL markdown formatting (headers, bullets, LaTeX)
7. Do NOT add, remove, or reinterpret content — only fix clear transcription errors
8. Return ONLY the corrected markdown with no explanation or commentary

Original transcription:
{raw_text}

Corrected markdown:
"""


def correct_ocr_output(
    raw_text: str,
    model: str = "mistral",
) -> str:
    """
    Run LLM correction pass on raw OCR output.

    Uses a text-only model (not vision) since we're working with text now.
    Mistral or llama3 are good defaults — fast and accurate for this task.

    Args:
        raw_text: Raw OCR output to correct.
        model: Ollama model name for correction (default: mistral).

    Returns:
        Corrected markdown text.
    """
    if raw_text.strip() in ("[BLANK_PAGE]", ""):
        return raw_text

    prompt = CORRECTION_PROMPT.format(raw_text=raw_text)

    response = ollama.generate(model=model, prompt=prompt)
    return response["response"].strip()


def estimate_correction_confidence(raw: str, corrected: str) -> float:
    """
    Estimate how much the correction changed the text.
    High change rate = potentially low-quality original OCR.
    Returns a score 0.0 (heavily changed) to 1.0 (unchanged).

    Computes the overlap of lowercased word sets:
    confidence = len(raw_words ∩ corrected_words) / len(raw_words)

    Returns:
        Score from 0.0 to 1.0. Returns 0.0 when raw is empty/whitespace-only;
        1.0 when raw words are a subset of corrected words.
    """
    if not raw or not raw.strip():
        return 0.0

    raw_words = set(raw.lower().split())
    corrected_words = set(corrected.lower().split())

    if not raw_words:
        return 1.0

    overlap = len(raw_words & corrected_words) / len(raw_words)
    return overlap
