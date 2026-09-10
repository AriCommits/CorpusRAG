"""Transcript cleaning logic."""

from pathlib import Path

from llm import create_backend

from .config import VideoConfig
from .pipeline_queue import ModelGates, default_gates


class TranscriptCleaner:
    """Clean raw transcripts using LLM."""

    # Signals to run_transcription_queue that the LLM call is gated here,
    # so the queue must not take gates.llm a second time.
    locks_internally = True

    def __init__(self, config: VideoConfig, gates: ModelGates | None = None):
        """Initialize transcript cleaner.

        Args:
            config: Video configuration
            gates: Optional model mutexes. Defaults to the process-local
                singleton so concurrent cleaners serialize the LLM.
        """
        self.config = config
        self._gates = gates if gates is not None else default_gates()
        # Initialize LLM backend for cleaning
        self.llm_backend = create_backend(config.llm.to_backend_config())

    def clean(self, transcript: str) -> str:
        """Clean a raw transcript using LLM.

        Args:
            transcript: Raw transcript text

        Returns:
            Cleaned transcript text
        """
        # Insert the transcript without interpreting other braces in the speech.
        prompt = self.config.clean_prompt.replace("{transcript}", transcript)

        # Call LLM backend (supports any configured backend: Ollama, OpenAI, etc.)
        with self._gates.llm:
            response = self.llm_backend.complete(prompt, model=self.config.clean_model)

        return response.text

    def clean_file(self, input_path: Path, output_path: Path | None = None) -> Path:
        """Clean a transcript file.

        Args:
            input_path: Path to raw transcript file
            output_path: Optional output path (defaults to input_path with '_cleaned' suffix)

        Returns:
            Path to cleaned transcript file
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Transcript not found: {input_path}")

        # Read raw transcript
        raw_text = input_path.read_text(encoding="utf-8")

        # Clean it
        cleaned_text = self.clean(raw_text)

        # Determine output path
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
        else:
            output_path = Path(output_path)

        # Write cleaned transcript
        output_path.write_text(cleaned_text, encoding="utf-8")

        return output_path
