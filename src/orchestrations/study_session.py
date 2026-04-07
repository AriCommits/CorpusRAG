"""
Study Session Orchestrator.

Combines summaries, flashcards, and quizzes for comprehensive study sessions.
"""

from typing import Any

from corpus_callosum.config import BaseConfig
from corpus_callosum.db import DatabaseBackend
from corpus_callosum.tools.flashcards import FlashcardConfig, FlashcardGenerator
from corpus_callosum.tools.quizzes import QuizConfig, QuizGenerator
from corpus_callosum.tools.summaries import SummaryConfig, SummaryGenerator


class StudySessionOrchestrator:
    """
    Orchestrates a complete study session workflow.
    
    Generates:
    1. Summary of the topic
    2. Flashcards for key concepts
    3. Quiz for self-assessment
    """
    
    def __init__(self, config: BaseConfig, db: DatabaseBackend):
        """
        Initialize the study session orchestrator.
        
        Args:
            config: Base configuration
            db: Database backend instance
        """
        self.config = config
        self.db = db
        
        # Initialize tool configs
        self.summary_config = SummaryConfig.from_dict(config.to_dict())
        self.flashcard_config = FlashcardConfig.from_dict(config.to_dict())
        self.quiz_config = QuizConfig.from_dict(config.to_dict())
    
    def create_session(
        self,
        collection: str,
        topic: str | None = None,
        flashcard_count: int = 15,
        quiz_count: int = 10,
        summary_length: str = "medium",
    ) -> dict[str, Any]:
        """
        Create a complete study session.
        
        Args:
            collection: Collection name containing study material
            topic: Optional specific topic to focus on
            flashcard_count: Number of flashcards to generate
            quiz_count: Number of quiz questions to generate
            summary_length: Summary length (short/medium/long)
        
        Returns:
            Dictionary with summary, flashcards, and quiz
        """
        # Generate summary
        self.summary_config.summary_length = summary_length
        summary_gen = SummaryGenerator(self.summary_config, self.db)
        summary = summary_gen.generate(collection, topic)
        
        # Generate flashcards
        self.flashcard_config.cards_per_topic = flashcard_count
        flashcard_gen = FlashcardGenerator(self.flashcard_config, self.db)
        flashcards = flashcard_gen.generate(collection)
        
        # Generate quiz
        self.quiz_config.questions_per_topic = quiz_count
        quiz_gen = QuizGenerator(self.quiz_config, self.db)
        quiz = quiz_gen.generate(collection)
        
        return {
            "collection": collection,
            "topic": topic,
            "summary": summary,
            "flashcards": flashcards,
            "quiz": quiz,
        }
    
    def format_session(self, session: dict[str, Any]) -> str:
        """
        Format a study session for display.
        
        Args:
            session: Study session data
        
        Returns:
            Formatted markdown string
        """
        topic_str = f" - {session['topic']}" if session['topic'] else ""
        
        output = f"""# Study Session: {session['collection']}{topic_str}

## Summary

{session['summary']}

---

## Flashcards ({len(session['flashcards'])} cards)

{session['flashcards']}

---

## Quiz ({session['quiz'].count('?')} questions)

{session['quiz']}
"""
        
        return output
