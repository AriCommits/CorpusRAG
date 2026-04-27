"""Learning-focused MCP tool functions (flashcards, summaries, quizzes, video)."""

from __future__ import annotations

from config import BaseConfig
from db import DatabaseBackend

_GENERATORS_ERROR = (
    "Flashcard generation requires 'generators' extra. "
    "Install: pip install corpusrag[generators]"
)
_SUMMARY_ERROR = (
    "Summary generation requires 'generators' extra. "
    "Install: pip install corpusrag[generators]"
)
_QUIZ_ERROR = (
    "Quiz generation requires 'generators' extra. "
    "Install: pip install corpusrag[generators]"
)


def generate_flashcards(
    collection: str,
    count: int,
    difficulty: str,
    config: BaseConfig,
    db: DatabaseBackend,
) -> dict:
    """Generate flashcards from a collection."""
    try:
        from tools.flashcards import GENERATORS_AVAILABLE, FlashcardConfig, FlashcardGenerator
    except ImportError:
        return {"status": "error", "error": _GENERATORS_ERROR}

    if not GENERATORS_AVAILABLE:
        return {"status": "error", "error": _GENERATORS_ERROR}

    try:
        from utils.validation import get_validator

        validator = get_validator()
        validated_collection = validator.validate_collection_name(collection)

        flashcard_config = FlashcardConfig.from_dict(config.to_dict())
        flashcard_config.cards_per_topic = count
        flashcard_config.difficulty_levels = [difficulty]

        generator = FlashcardGenerator(flashcard_config, db)
        flashcards = generator.generate(validated_collection)

        return {
            "status": "success",
            "collection": collection,
            "count": len(flashcards),
            "flashcards": flashcards,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_summary(
    collection: str,
    topic: str | None,
    length: str,
    config: BaseConfig,
    db: DatabaseBackend,
) -> dict:
    """Generate a summary from a collection."""
    try:
        from tools.summaries import GENERATORS_AVAILABLE, SummaryConfig, SummaryGenerator
    except ImportError:
        return {"status": "error", "error": _SUMMARY_ERROR}

    if not GENERATORS_AVAILABLE:
        return {"status": "error", "error": _SUMMARY_ERROR}

    try:
        summary_config = SummaryConfig.from_dict(config.to_dict())
        summary_config.summary_length = length

        generator = SummaryGenerator(summary_config, db)
        summary = generator.generate(collection, topic)

        return {
            "status": "success",
            "collection": collection,
            "topic": topic,
            "summary": summary,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_quiz(
    collection: str,
    count: int,
    question_types: list[str] | None,
    config: BaseConfig,
    db: DatabaseBackend,
) -> dict:
    """Generate a quiz from a collection."""
    try:
        from tools.quizzes import GENERATORS_AVAILABLE, QuizConfig, QuizGenerator
    except ImportError:
        return {"status": "error", "error": _QUIZ_ERROR}

    if not GENERATORS_AVAILABLE:
        return {"status": "error", "error": _QUIZ_ERROR}

    try:
        quiz_config = QuizConfig.from_dict(config.to_dict())
        quiz_config.questions_per_topic = count
        if question_types:
            quiz_config.question_types = question_types

        generator = QuizGenerator(quiz_config, db)
        quiz = generator.generate(collection)

        return {
            "status": "success",
            "collection": collection,
            "count": count,
            "quiz": quiz,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def transcribe_video(
    video_path: str,
    collection: str,
    model: str,
    config: BaseConfig,
    db: DatabaseBackend,
) -> dict:
    """Transcribe a video file using Whisper."""
    try:
        from tools.video import VideoConfig, VideoTranscriber

        video_config = VideoConfig.from_dict(config.to_dict())
        video_config.whisper_model = model

        transcriber = VideoTranscriber(video_config, db)
        transcript = transcriber.transcribe_file(video_path, collection)

        return {
            "status": "success",
            "video_path": video_path,
            "collection": collection,
            "transcript": transcript,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def clean_transcript(
    transcript_text: str,
    model: str | None,
    config: BaseConfig,
) -> dict:
    """Clean and format a transcript using LLM."""
    try:
        from tools.video import TranscriptCleaner, VideoConfig

        video_config = VideoConfig.from_dict(config.to_dict())
        if model:
            video_config.clean_model = model

        cleaner = TranscriptCleaner(video_config)
        cleaned = cleaner.clean(transcript_text)

        return {"status": "success", "cleaned_transcript": cleaned}
    except Exception as e:
        return {"status": "error", "error": str(e)}
