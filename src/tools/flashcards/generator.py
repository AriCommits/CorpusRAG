"""Flashcard generation logic."""

import logging
import re
from typing import Optional

from corpus_callosum.db import DatabaseBackend
from corpus_callosum.llm import create_backend, PromptTemplates

from .config import FlashcardConfig

logger = logging.getLogger(__name__)


class FlashcardGenerator:
    """Generate flashcards from documents in a collection."""

    def __init__(self, config: FlashcardConfig, db: DatabaseBackend):
        """Initialize flashcard generator.

        Args:
            config: Flashcard configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        # Create LLM backend for generation
        self.llm_backend = create_backend(config.llm.to_backend_config())

    def generate(
        self, collection: str, difficulty: str = "intermediate", count: Optional[int] = None
    ) -> list[dict[str, str]]:
        """Generate flashcards from collection.

        Args:
            collection: Collection name
            difficulty: Difficulty level
            count: Number of cards to generate (uses config default if None)

        Returns:
            List of flashcard dicts with 'front' and 'back' keys
        """
        if count is None:
            count = self.config.cards_per_topic

        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Check if collection exists
        if not self.db.collection_exists(full_collection):
            raise ValueError(f"Collection '{full_collection}' does not exist")

        # Retrieve documents from the collection
        try:
            # Get a sample of documents from the collection
            # Using a simple query to get representative content
            sample_docs = self.db.query(
                collection=full_collection,
                query="main concepts key ideas important information",
                top_k=10,
            )
            
            if not sample_docs:
                logger.warning(f"No documents found in collection '{full_collection}'")
                return self._generate_placeholder_flashcards(count, difficulty, collection)
            
            # Extract document texts
            document_texts = [doc.text for doc in sample_docs]
            
            # Generate flashcards using LLM
            flashcards = self._generate_with_llm(
                document_texts, difficulty=difficulty, count=count, topic=collection
            )
            
            # Add metadata to each flashcard
            for card in flashcards:
                card.update({
                    "difficulty": difficulty,
                    "collection": collection,
                })
            
            return flashcards
            
        except Exception as e:
            logger.error(f"Error generating flashcards: {e}")
            # Fall back to placeholder flashcards
            return self._generate_placeholder_flashcards(count, difficulty, collection)

    def _generate_with_llm(
        self,
        documents: list[str],
        difficulty: str,
        count: int,
        topic: str | None = None,
    ) -> list[dict[str, str]]:
        """Generate flashcards using LLM.
        
        Args:
            documents: List of document texts
            difficulty: Difficulty level
            count: Number of flashcards to generate
            topic: Optional topic for focused generation
            
        Returns:
            List of flashcard dictionaries
        """
        # Create prompt using template
        prompt = PromptTemplates.flashcard_generation(
            documents=documents,
            difficulty=difficulty,
            count=count,
            topic=topic,
        )
        
        try:
            # Generate content using LLM
            response = self.llm_backend.complete(prompt)
            
            # Parse the response into flashcards
            flashcards = self._parse_flashcard_response(response.text)
            
            # Ensure we have the right number of flashcards
            if len(flashcards) < count:
                logger.warning(
                    f"Generated {len(flashcards)} flashcards, expected {count}. "
                    "Padding with placeholders."
                )
                # Pad with placeholders if needed
                for i in range(len(flashcards), count):
                    flashcards.append({
                        "front": f"Additional Question {i+1-len(flashcards)} ({difficulty})",
                        "back": f"Additional Answer {i+1-len(flashcards)}",
                    })
            elif len(flashcards) > count:
                # Trim to requested count
                flashcards = flashcards[:count]
            
            return flashcards
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fall back to placeholder generation
            return []

    def _parse_flashcard_response(self, response_text: str) -> list[dict[str, str]]:
        """Parse LLM response into flashcard format.
        
        Args:
            response_text: Raw LLM response text
            
        Returns:
            List of flashcard dictionaries
        """
        flashcards = []
        
        # Split response into potential flashcard sections
        sections = re.split(r'\n\s*---\s*\n|\n\n+', response_text)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # Look for Q: ... A: ... pattern
            q_match = re.search(r'Q:\s*(.+?)(?=A:|$)', section, re.DOTALL | re.IGNORECASE)
            a_match = re.search(r'A:\s*(.+?)(?=Q:|$)', section, re.DOTALL | re.IGNORECASE)
            
            if q_match and a_match:
                question = q_match.group(1).strip()
                answer = a_match.group(1).strip()
                
                # Clean up the text (remove extra whitespace, line breaks)
                question = ' '.join(question.split())
                answer = ' '.join(answer.split())
                
                if question and answer:
                    flashcards.append({
                        "front": question,
                        "back": answer,
                    })
        
        return flashcards

    def _generate_placeholder_flashcards(
        self, count: int, difficulty: str, collection: str
    ) -> list[dict[str, str]]:
        """Generate placeholder flashcards as fallback.
        
        Args:
            count: Number of flashcards to generate
            difficulty: Difficulty level
            collection: Collection name
            
        Returns:
            List of placeholder flashcard dictionaries
        """
        flashcards = []
        for i in range(count):
            flashcards.append(
                {
                    "front": f"Question {i+1} ({difficulty}) - Collection: {collection}",
                    "back": f"Answer {i+1} - Please regenerate with working LLM connection",
                    "difficulty": difficulty,
                    "collection": collection,
                }
            )
        return flashcards

    def format_flashcards(self, flashcards: list[dict[str, str]]) -> str:
        """Format flashcards according to config format.

        Args:
            flashcards: List of flashcard dicts

        Returns:
            Formatted flashcards string
        """
        if self.config.format == "anki":
            return self._format_anki(flashcards)
        elif self.config.format == "quizlet":
            return self._format_quizlet(flashcards)
        else:  # plain
            return self._format_plain(flashcards)

    def _format_anki(self, flashcards: list[dict[str, str]]) -> str:
        """Format as Anki import format."""
        lines = []
        for card in flashcards:
            lines.append(f"{card['front']}\t{card['back']}")
        return "\n".join(lines)

    def _format_quizlet(self, flashcards: list[dict[str, str]]) -> str:
        """Format as Quizlet import format."""
        lines = []
        for card in flashcards:
            lines.append(f"{card['front']}\t{card['back']}")
        return "\n".join(lines)

    def _format_plain(self, flashcards: list[dict[str, str]]) -> str:
        """Format as plain text."""
        lines = []
        for i, card in enumerate(flashcards, 1):
            lines.append(f"Card {i}:")
            lines.append(f"Q: {card['front']}")
            lines.append(f"A: {card['back']}")
            lines.append("")
        return "\n".join(lines)
