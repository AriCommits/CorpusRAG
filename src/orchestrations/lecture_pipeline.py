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

# Imported from the submodules directly (rather than the ``tools.video``
# package) so they stay lightweight and are individually patchable at
# ``orchestrations.lecture_pipeline.<name>`` in tests.
from tools.video.discover import discover_media_files
from tools.video.pipeline_queue import ModelGates, run_transcription_queue


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

        # Steps 3-6: ingest + generators (shared with process_course).
        return self._generate_materials(
            transcript=transcript,
            course=course,
            lecture_num=lecture_num,
            collection_name=collection_name,
            resolved_flashcard_count=resolved_flashcard_count,
            resolved_quiz_count=resolved_quiz_count,
            resolved_summary_length=resolved_summary_length,
            do_summary=do_summary,
            do_flashcards=do_flashcards,
            do_quiz=do_quiz,
        )

    def _generate_materials(
        self,
        *,
        transcript: str,
        course: str,
        lecture_num: int,
        collection_name: str,
        resolved_flashcard_count: int | None,
        resolved_quiz_count: int | None,
        resolved_summary_length: str,
        do_summary: bool,
        do_flashcards: bool,
        do_quiz: bool,
    ) -> dict[str, Any]:
        """Ingest an (already transcribed/cleaned) transcript and build materials.

        This holds the identical ingest -> summary -> flashcards -> quiz
        semantics used by :meth:`process_lecture`. It is factored out so
        :meth:`process_course` can reuse it for each queued result **without**
        re-transcribing or re-cleaning.
        """
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
        Process all lecture videos in a folder (recursively).

        Discovery, transcription and cleaning run through the shared
        transcription queue so that a single Whisper weight load and a single
        LLM cleaner are reused across every file, Whisper stays exclusive and
        audio-extract overlaps Whisper. Only **after** the queue drains does
        each successful transcript flow through the same ingest / summary /
        flashcards / quiz steps used by :meth:`process_lecture` — generators
        never overlap the queue.

        Args:
            video_folder: Folder containing video files (searched recursively)
            course: Course identifier
            skip_clean: Skip transcript cleaning step (config fallback)

        Returns:
            List of lecture processing results, one per successfully
            transcribed file, in sorted source order.
        """
        # Resolve the same run options process_lecture would use so course
        # runs honor config-level defaults identically.
        resolved_skip_clean = bool(self._resolve(skip_clean, "skip_clean", False))
        resolved_flashcard_count = self._resolve(None, "flashcard_count")
        resolved_quiz_count = self._resolve(None, "quiz_count")
        resolved_summary_length = self._resolve(
            None, "summary_length", self.summary_config.summary_length
        )
        do_summary = bool(self._resolve(None, "generate_summary", True))
        do_flashcards = bool(self._resolve(None, "generate_flashcards", True))
        do_quiz = bool(self._resolve(None, "generate_quiz", True))

        # Discover media files recursively, replacing the old hardcoded list.
        video_files = discover_media_files(
            video_folder,
            self.video_config.supported_extensions,
            recursive=True,
        )

        # One shared set of models/mutexes for the whole course.
        gates = ModelGates()
        transcriber = VideoTranscriber(self.video_config, gates=gates)
        cleaner = None if resolved_skip_clean else TranscriptCleaner(self.video_config, gates=gates)

        # Transcribe (+ clean) every file. Blocks until the queue drains.
        queue_results = run_transcription_queue(
            video_files,
            transcriber=transcriber,
            cleaner=cleaner,
            skip_clean=resolved_skip_clean,
            gates=gates,
        )

        # Only after the queue finishes: run generators per successful result,
        # in sorted source order. Failed files are skipped.
        successful = sorted(
            (r for r in queue_results if r.error is None and r.raw is not None),
            key=lambda r: r.source,
        )

        results: list[dict[str, Any]] = []
        for lecture_num, job in enumerate(successful, start=1):
            # Prefer the cleaned transcript when cleaning ran; otherwise raw.
            transcript = job.cleaned if job.cleaned is not None else job.raw
            collection_name = f"{course}_Lecture{lecture_num:02d}"
            result = self._generate_materials(
                transcript=transcript,
                course=course,
                lecture_num=lecture_num,
                collection_name=collection_name,
                resolved_flashcard_count=resolved_flashcard_count,
                resolved_quiz_count=resolved_quiz_count,
                resolved_summary_length=resolved_summary_length,
                do_summary=do_summary,
                do_flashcards=do_flashcards,
                do_quiz=do_quiz,
            )
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
