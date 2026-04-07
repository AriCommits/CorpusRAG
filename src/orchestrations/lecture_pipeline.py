"""
Lecture Pipeline Orchestrator.

Processes lecture videos into comprehensive study materials.
"""

from pathlib import Path
from typing import Any

from corpus_callosum.config import BaseConfig
from corpus_callosum.db import DatabaseBackend
from corpus_callosum.tools.flashcards import FlashcardConfig, FlashcardGenerator
from corpus_callosum.tools.quizzes import QuizConfig, QuizGenerator
from corpus_callosum.tools.rag import RAGConfig, RAGIngester
from corpus_callosum.tools.summaries import SummaryConfig, SummaryGenerator
from corpus_callosum.tools.video import (
    TranscriptCleaner,
    VideoConfig,
    VideoTranscriber,
)


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
        
        # Initialize tool configs
        self.video_config = VideoConfig.from_dict(config.to_dict())
        self.rag_config = RAGConfig.from_dict(config.to_dict())
        self.summary_config = SummaryConfig.from_dict(config.to_dict())
        self.flashcard_config = FlashcardConfig.from_dict(config.to_dict())
        self.quiz_config = QuizConfig.from_dict(config.to_dict())
    
    def process_lecture(
        self,
        video_path: Path,
        course: str,
        lecture_num: int,
        skip_clean: bool = False,
    ) -> dict[str, Any]:
        """
        Process a single lecture video into study materials.
        
        Args:
            video_path: Path to video file
            course: Course identifier (e.g., BIOL101)
            lecture_num: Lecture number
            skip_clean: Skip transcript cleaning step
        
        Returns:
            Dictionary with all generated materials
        """
        collection_name = f"{course}_Lecture{lecture_num:02d}"
        
        # Step 1: Transcribe
        transcriber = VideoTranscriber(self.video_config, self.db)
        transcript = transcriber.transcribe_file(video_path, collection_name)
        
        # Step 2: Clean (optional)
        if not skip_clean:
            cleaner = TranscriptCleaner(self.video_config)
            transcript = cleaner.clean(transcript)
        
        # Step 3: Ingest into RAG
        # Save transcript to temp file for ingestion
        temp_transcript = Path(f"/tmp/{collection_name}_transcript.md")
        temp_transcript.write_text(transcript)
        
        ingester = RAGIngester(self.rag_config, self.db)
        ingest_result = ingester.ingest_path(temp_transcript, collection_name)
        
        # Step 4: Generate summary
        summary_gen = SummaryGenerator(self.summary_config, self.db)
        summary = summary_gen.generate(collection_name)
        
        # Step 5: Generate flashcards
        flashcard_gen = FlashcardGenerator(self.flashcard_config, self.db)
        flashcards = flashcard_gen.generate(collection_name)
        
        # Step 6: Generate quiz
        quiz_gen = QuizGenerator(self.quiz_config, self.db)
        quiz = quiz_gen.generate(collection_name)
        
        return {
            "course": course,
            "lecture_num": lecture_num,
            "collection": collection_name,
            "transcript": transcript,
            "chunks_indexed": ingest_result.chunks_created,
            "summary": summary,
            "flashcards": flashcards,
            "quiz": quiz,
        }
    
    def process_course(
        self,
        video_folder: Path,
        course: str,
        skip_clean: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Process all lecture videos in a folder.
        
        Args:
            video_folder: Folder containing video files
            course: Course identifier
            skip_clean: Skip transcript cleaning step
        
        Returns:
            List of lecture processing results
        """
        results = []
        
        # Find all video files
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        video_files = sorted([
            f for f in video_folder.iterdir()
            if f.suffix.lower() in video_extensions
        ])
        
        # Process each video
        for idx, video_file in enumerate(video_files, start=1):
            result = self.process_lecture(video_file, course, idx, skip_clean)
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
        output = f"""# {result['course']} - Lecture {result['lecture_num']}

## Transcript

{result['transcript']}

---

## Summary

{result['summary']}

---

## Flashcards

{result['flashcards']}

---

## Quiz

{result['quiz']}
"""
        
        return output
