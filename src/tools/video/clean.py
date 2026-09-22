"""Transcript cleaning logic."""

from pathlib import Path

from llm import create_backend

from .config import VideoConfig
from .pipeline_queue import ModelGates, default_gates

_CLEAN_SYSTEM = (
    "You are a lecture-transcript editor. Reply with ONLY the cleaned "
    "transcript. Do not restate these instructions, do not ask the user to "
    "paste a transcript, and do not wrap the result in commentary."
)


def render_clean_prompt(template: str, transcript: str) -> str:
    """Build the user prompt, always including the raw transcript.

    YAML templates that omit ``{transcript}`` still get the text appended so
    the model cannot answer the instructions in the abstract.
    """
    template = template or ""
    if "{transcript}" in template:
        return template.replace("{transcript}", transcript)
    return template.rstrip() + "\n\nTranscript:\n" + transcript


class TranscriptCleaner:
    """Clean raw transcripts using LLM."""

    locks_internally = True

    def __init__(self, config: VideoConfig, gates: ModelGates | None = None):
        self.config = config
        self._gates = gates if gates is not None else default_gates()
        self.llm_backend = create_backend(config.llm.to_backend_config())

    def clean(self, transcript: str) -> str:
        """Clean a raw transcript using LLM."""
        user_prompt = render_clean_prompt(self.config.clean_prompt, transcript)
        messages = [
            {"role": "system", "content": _CLEAN_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
        with self._gates.llm:
            try:
                response = self.llm_backend.chat(messages, model=self.config.clean_model)
            except Exception:
                response = self.llm_backend.complete(user_prompt, model=self.config.clean_model)
        return (response.text or "").strip()

    def clean_file(self, input_path: Path, output_path: Path | None = None) -> Path:
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Transcript not found: {input_path}")

        raw_text = input_path.read_text(encoding="utf-8")
        cleaned_text = self.clean(raw_text)

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
        else:
            output_path = Path(output_path)

        output_path.write_text(cleaned_text, encoding="utf-8")
        return output_path
