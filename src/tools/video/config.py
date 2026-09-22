"""Video tool configuration."""

from pathlib import Path
from typing import Any

from pydantic import Field

from config.base import BaseConfig


class VideoConfig(BaseConfig):
    """Video transcription and processing configuration."""

    # Transcription settings
    whisper_model: str = "medium.en"
    whisper_device: str = "cuda"  # cuda | cpu
    whisper_compute_type: str = "float16"
    whisper_language: str = "en"
    models_dir: str = Field(default_factory=lambda: str(Path.home() / "models" / "whisper"))

    # Cleaning settings
    clean_model: str = "qwen3:8b"
    clean_ollama_host: str = "http://localhost:11434"
    clean_prompt: str = """\
Clean this lecture transcript into structured markdown notes.
- Remove filler words, false starts, and repetition
- Preserve all specific facts, definitions, numbers, and examples exactly
- Use ## headers to separate distinct topics as they appear
- Preserve the segment markers (e.g. ## Segment 1: filename) exactly as they are
- Do not summarize away any detail — only remove noise
- Reply with only the cleaned transcript, not a restatement of these rules

Transcript:
{transcript}
"""

    # Audio extraction settings
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    keep_extracted_audio: bool = False
    audio_timeout_seconds: float = 1800.0

    # Output settings
    output_format: str = "markdown"
    include_timestamps: bool = False
    collection_prefix: str = "videos"

    # Supported video extensions
    supported_extensions: list[str] = Field(
        default_factory=lambda: [
            ".mp4",
            ".mkv",
            ".mov",
            ".avi",
            ".webm",
            ".m4v",
            ".zoom",
        ]
    )

    # OCR settings
    vision_model: str = "llava"
    scene_threshold: float = 0.3
    min_frame_interval: float = 2.0
    use_latex_fallback: bool = True
    dedup_threshold: float = 0.85
    context_window: int = 1
    slide_ocr_prompt: str = ""
    chalkboard_ocr_prompt: str = ""

    # Job settings
    max_concurrent_jobs: int = 2
    job_expiry_seconds: int = 3600

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoConfig":
        """Create videoconfig from dictionary."""
        base_config, tool_data = BaseConfig.split_section(data, "video")
        merged = base_config.model_dump(exclude={"raw"})
        merged.update(tool_data)

        # Preserve specific backward-compatibility logic for video
        if "video" == "video":
            if "clean_ollama_host" not in merged:
                merged["clean_ollama_host"] = base_config.llm.endpoint

        inst = cls.model_validate(merged)
        inst.raw = data
        return inst
