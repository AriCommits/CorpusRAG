"""Video transcription logic."""

import uuid
from datetime import date
from pathlib import Path

from . import audio
from .config import VideoConfig
from .pipeline_queue import ModelGates, default_gates


class VideoTranscriber:
    """Transcribe video files using Whisper."""

    # Signals to run_transcription_queue that the Whisper call is gated here,
    # so the queue must not take gates.whisper a second time.
    locks_internally = True

    def __init__(self, config: VideoConfig, gates: ModelGates | None = None):
        """Initialize video transcriber.

        Args:
            config: Video configuration
            gates: Optional model mutexes. Defaults to the process-local
                singleton so concurrent transcribers serialize Whisper.
        """
        self.config = config
        self._model = None
        self._gates = gates if gates is not None else default_gates()

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

        Extracts a WAV audio track into ``scratch/audio`` and runs Whisper on
        that audio rather than the video container. The extracted WAV is removed
        afterwards unless ``config.keep_extracted_audio`` is set.

        Args:
            video_path: Path to video file

        Returns:
            Raw transcript text
        """
        video_path = Path(video_path)

        audio_dir = Path(self.config.paths.scratch_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = (
            video_path.stem.replace("/", "_").replace("\\", "_").replace("..", "_")
        ) or "audio"
        wav = audio_dir / f"{safe_stem}_{uuid.uuid4().hex[:8]}.wav"

        try:
            audio.extract_audio(
                video_path,
                wav,
                sample_rate=self.config.audio_sample_rate,
                channels=self.config.audio_channels,
                allowed_root=audio_dir.resolve(),
                timeout=float(getattr(self.config, "audio_timeout_seconds", 1800)),
            )

            language = self.config.whisper_language or None
            # faster-whisper yields segments lazily, so the actual compute
            # happens while iterating. Hold the whisper gate across model load
            # AND iteration so two workers cannot both construct WhisperModel.
            # audio extraction above stays unlocked and can overlap.
            lines = []
            with self._gates.whisper:
                model = self._load_model()
                segments, _ = model.transcribe(str(wav), language=language)
                for segment in segments:
                    text = segment.text.strip()
                    if self.config.include_timestamps:
                        lines.append(f"[{segment.start:.2f}s - {segment.end:.2f}s] {text}")
                    else:
                        lines.append(text)

            return "\n".join(lines)
        finally:
            if not self.config.keep_extracted_audio:
                wav.unlink(missing_ok=True)

    def transcribe_folder(
        self,
        input_folder: Path,
        course: str | None = None,
        lecture: int | None = None,
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
            f
            for f in input_folder.iterdir()
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
        course: str | None = None,
        lecture: int | None = None,
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
