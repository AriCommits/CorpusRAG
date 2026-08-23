"""
Lecture Pipeline Orchestrator.

Processes lecture videos into comprehensive study materials.
"""

from pathlib import Path
from typing import Any

from config import BaseConfig
from db import DatabaseBackend
from tools.flashcards import FlashcardConfig, FlashcardGenerator
from tools.quizzes import QuizConfig, QuizGenerator
from tools.rag import RAGConfig, RAGIngester
from tools.summaries import SummaryConfig, SummaryGenerator
from tools.video import TranscriptCleaner, VideoConfig, VideoTranscriber


class LecturePipelineOrchestrator:
    """
    Orchestrates processing of lecture videos into study materials.

    Pipeline steps:
    1. Transcribe video(s)
    2. Clean transcript
    3. Ingest into RAG collection
    4. Generate summary
    5. Generate flashcards
    6. Generate quiz
    """

    def __init__(self, config: BaseConfig, db: DatabaseBackend):
        """
        Initialize the lecture pipeline orchestrator.

        Args:
            config: Base configuration
            db: Database backend instance
        """
        self.config = config
        self.db = db

        # Build every sub-tool config from the FULL merged document so that
        # tool-specific sections (video/rag/summaries/flashcards/quizzes) are
        # honored rather than being reset to defaults. ``raw`` holds the whole
        # loaded document; fall back to ``to_dict()`` for configs constructed
        # directly (e.g. in unit tests) where ``raw`` is empty.
        merged = self.config.raw or self.config.to_dict()

        self.video_config = VideoConfig.from_dict(merged)
        self.rag_config = RAGConfig.from_dict(merged)
        self.summary_config = SummaryConfig.from_dict(merged)
        self.flashcard_config = FlashcardConfig.from_dict(merged)
        self.quiz_config = QuizConfig.from_dict(merged)

        # Pipeline-level defaults (counts, summary length, feature toggles).
        self.pipeline_opts = (merged.get("orchestrations", {}) or {}).get("lecture_pipeline", {})

    def _resolve(self, override: Any, key: str, default: Any = None) -> Any:
        """Resolve a value: explicit override wins, then config, then default."""
        if override is not None:
            return override
        value = self.pipeline_opts.get(key)
        if value is not None:
            return value
        return default

    def process_lecture(
        self,
        video_path: Path,
        course: str,
        lecture_num: int,
        skip_clean: bool | None = None,
        flashcard_count: int | None = None,
        quiz_count: int | None = None,
        summary_length: str | None = None,
        generate_summary: bool | None = None,
        generate_flashcards: bool | None = None,
        generate_quiz: bool | None = None,
    ) -> dict[str, Any]:
        """
        Process a single lecture video into study materials.

        Every optional argument falls back to the configured
        ``orchestrations.lecture_pipeline`` value when left as ``None``.

        Args:
            video_path: Path to video file
            course: Course identifier (e.g., BIOL101)
            lecture_num: Lecture number
            skip_clean: Skip transcript cleaning step (config fallback)
            flashcard_count: Number of flashcards to generate (config fallback)
            quiz_count: Number of quiz questions to generate (config fallback)
            summary_length: Summary length short|medium|long (config fallback)
            generate_summary: Toggle summary generation (config fallback, default True)
            generate_flashcards: Toggle flashcard generation (config fallback, default True)
            generate_quiz: Toggle quiz generation (config fallback, default True)

        Returns:
            Dictionary with all generated materials
        """
        collection_name = f"{course}_Lecture{lecture_num:02d}"

        # Resolve run options from explicit args -> config -> defaults.
        resolved_skip_clean = bool(self._resolve(skip_clean, "skip_clean", False))
        resolved_flashcard_count = self._resolve(flashcard_count, "flashcard_count")
        resolved_quiz_count = self._resolve(quiz_count, "quiz_count")
        resolved_summary_length = self._resolve(
            summary_length, "summary_length", self.summary_config.summary_length
        )
        do_summary = bool(self._resolve(generate_summary, "generate_summary", True))
        do_flashcards = bool(self._resolve(generate_flashcards, "generate_flashcards", True))
        do_quiz = bool(self._resolve(generate_quiz, "generate_quiz", True))

        # Step 1: Transcribe
        transcriber = VideoTranscriber(self.video_config)
        transcript = transcriber.transcribe_file(video_path)

        # Step 2: Clean (optional)
        if not resolved_skip_clean:
            cleaner = TranscriptCleaner(self.video_config)
            transcript = cleaner.clean(transcript)

        # Step 3: Ingest into RAG
        # Save transcript to temp file for ingestion
        scratch_dir = self.video_config.paths.scratch_dir
        scratch_dir.mkdir(parents=True, exist_ok=True)
        temp_transcript = scratch_dir / f"{collection_name}_transcript.md"
        temp_transcript.write_text(transcript)

        ingester = RAGIngester(self.rag_config, self.db)
        ingest_result = ingester.ingest_path(temp_transcript, collection_name)

        # Step 4: Generate summary (honors configured summary_length via config)
        summary = None
        if do_summary:
            self.summary_config.summary_length = resolved_summary_length
            summary_gen = SummaryGenerator(self.summary_config, self.db)
            summary = summary_gen.generate(collection_name)

        # Step 5: Generate flashcards (count routed via the generate() param)
        flashcards = None
        if do_flashcards:
            flashcard_gen = FlashcardGenerator(self.flashcard_config, self.db)
            flashcards = flashcard_gen.generate(collection_name, count=resolved_flashcard_count)

        # Step 6: Generate quiz (count routed via the generate() param)
        quiz = None
        if do_quiz:
            quiz_gen = QuizGenerator(self.quiz_config, self.db)
            quiz = quiz_gen.generate(collection_name, count=resolved_quiz_count)

        return {
            "course": course,
            "lecture_num": lecture_num,
            "collection": collection_name,
            "transcript": transcript,
            "chunks_indexed": ingest_result.chunks_indexed,
            "summary": summary,
            "flashcards": flashcards,
            "quiz": quiz,
        }

    def process_course(
        self,
        video_folder: Path,
        course: str,
        skip_clean: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process all lecture videos in a folder.

        Args:
            video_folder: Folder containing video files
            course: Course identifier
            skip_clean: Skip transcript cleaning step (config fallback)

        Returns:
            List of lecture processing results
        """
        results = []

        # Find all video files
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        video_files = sorted(
            [f for f in video_folder.iterdir() if f.suffix.lower() in video_extensions]
        )

        # Process each video
        for idx, video_file in enumerate(video_files, start=1):
            result = self.process_lecture(video_file, course, idx, skip_clean=skip_clean)
            results.append(result)

        return results

    def format_lecture_materials(self, result: dict[str, Any]) -> str:
        """
        Format lecture materials for output.

        Args:
            result: Lecture processing result

        Returns:
            Formatted markdown string
        """
        output = f"""# {result["course"]} - Lecture {result["lecture_num"]}

## Transcript

{result["transcript"]}

---

## Summary

{result["summary"]}

---

## Flashcards

{result["flashcards"]}

---

## Quiz

{result["quiz"]}
"""

        return output
