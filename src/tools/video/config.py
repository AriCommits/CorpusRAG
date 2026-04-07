"""Video tool configuration."""

from dataclasses import dataclass, field
from pathlib import Path

from corpus_callosum.config.base import BaseConfig


@dataclass
class VideoConfig(BaseConfig):
    """Video transcription and processing configuration."""

    # Transcription settings
    whisper_model: str = "medium.en"
    whisper_device: str = "cuda"  # cuda | cpu
    whisper_compute_type: str = "float16"
    whisper_language: str = "en"
    models_dir: str = field(default_factory=lambda: str(Path.home() / "models" / "whisper"))
    
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

Transcript:
{transcript}
"""
    
    # Output settings
    output_format: str = "markdown"
    include_timestamps: bool = False
    collection_prefix: str = "videos"
    
    # Supported video extensions
    supported_extensions: list[str] = field(
        default_factory=lambda: [".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".zoom"]
    )

    @classmethod
    def from_dict(cls, data: dict) -> "VideoConfig":
        """Create video config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            VideoConfig instance
        """
        # Get base config
        base_config = super().from_dict(data)

        # Get video-specific config
        video_data = data.get("video", {})

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            whisper_model=video_data.get("whisper_model", "medium.en"),
            whisper_device=video_data.get("whisper_device", "cuda"),
            whisper_compute_type=video_data.get("whisper_compute_type", "float16"),
            whisper_language=video_data.get("whisper_language", "en"),
            models_dir=video_data.get("models_dir", str(Path.home() / "models" / "whisper")),
            clean_model=video_data.get("clean_model", "qwen3:8b"),
            clean_ollama_host=video_data.get("clean_ollama_host", "http://localhost:11434"),
            clean_prompt=video_data.get("clean_prompt", cls.__dataclass_fields__["clean_prompt"].default),
            output_format=video_data.get("output_format", "markdown"),
            include_timestamps=video_data.get("include_timestamps", False),
            collection_prefix=video_data.get("collection_prefix", "videos"),
            supported_extensions=video_data.get(
                "supported_extensions",
                [".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".zoom"]
            ),
        )
