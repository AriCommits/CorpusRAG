"""Video transcription logic."""

from datetime import date
from pathlib import Path
from typing import Optional

from .config import VideoConfig


class VideoTranscriber:
    """Transcribe video files using Whisper."""

    def __init__(self, config: VideoConfig):
        """Initialize video transcriber.

        Args:
            config: Video configuration
        """
        self.config = config
        self._model = None

    def _load_model(self):
        """Lazy-load the Whisper model."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise ImportError(
                    "faster-whisper is required for transcription. "
                    "Install with: pip install faster-whisper"
                )

            self._model = WhisperModel(
                self.config.whisper_model,
                device=self.config.whisper_device,
                compute_type=self.config.whisper_compute_type,
                download_root=self.config.models_dir,
            )
        return self._model

    def transcribe_file(self, video_path: Path) -> str:
        """Transcribe a single video file.

        Args:
            video_path: Path to video file

        Returns:
            Raw transcript text
        """
        model = self._load_model()
        language = self.config.whisper_language or None
        segments, _ = model.transcribe(str(video_path), language=language)
        
        lines = []
        for segment in segments:
            text = segment.text.strip()
            if self.config.include_timestamps:
                lines.append(f"[{segment.start:.2f}s - {segment.end:.2f}s] {text}")
            else:
                lines.append(text)
        
        return "\n".join(lines)

    def transcribe_folder(
        self,
        input_folder: Path,
        course: Optional[str] = None,
        lecture: Optional[int] = None,
    ) -> dict[str, str]:
        """Transcribe all videos in a folder.

        Args:
            input_folder: Folder containing video files
            course: Optional course identifier (e.g., "BIOL101")
            lecture: Optional lecture number

        Returns:
            Dictionary mapping video filename to transcript text
        """
        input_folder = Path(input_folder)
        videos = sorted(
            f for f in input_folder.iterdir()
            if f.suffix.lower() in self.config.supported_extensions
        )

        if not videos:
            raise FileNotFoundError(
                f"No supported video files found in {input_folder}\n"
                f"Supported formats: {', '.join(self.config.supported_extensions)}"
            )

        transcripts = {}
        for video in videos:
            transcripts[video.name] = self.transcribe_file(video)

        return transcripts

    def combine_transcripts(
        self,
        transcripts: dict[str, str],
        course: Optional[str] = None,
        lecture: Optional[int] = None,
    ) -> str:
        """Combine multiple transcripts into a single markdown document.

        Args:
            transcripts: Dictionary mapping filenames to transcript text
            course: Optional course identifier
            lecture: Optional lecture number

        Returns:
            Combined markdown transcript
        """
        lines = []
        
        # Add header if course/lecture provided
        if course or lecture:
            title_parts = []
            if course:
                title_parts.append(course.upper())
            if lecture:
                title_parts.append(f"Lecture {lecture}")
            lines.append(f"# {' - '.join(title_parts)}")
            lines.append(f"*Transcribed: {date.today().strftime('%Y-%m-%d')}*")
            lines.append("")

        # Add each transcript as a segment
        for i, (filename, transcript) in enumerate(transcripts.items(), 1):
            lines.append(f"## Segment {i}: {filename}")
            lines.append("")
            lines.append(transcript)
            lines.append("")

        return "\n".join(lines)
