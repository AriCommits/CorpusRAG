"""Flashcard generation logic."""

import logging
import re

from db import DatabaseBackend
from llm import PromptTemplates
from tools.generation import complete_prompt, sample_documents

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

    def generate(
        self,
        collection: str,
        difficulty: str = "intermediate",
        count: int | None = None,
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

        document_texts = sample_documents(
            self.db,
            self.config,
            collection,
            query_text="main concepts key ideas important information",
            n_results=10,
        )

        flashcards = self._generate_with_llm(
            document_texts, difficulty=difficulty, count=count, topic=collection
        )

        # Add metadata to each flashcard
        for card in flashcards:
            card.update(
                {
                    "difficulty": difficulty,
                    "collection": collection,
                }
            )

        return flashcards

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
            response_text = complete_prompt(self.config, prompt)

            # Parse the response into flashcards
            flashcards = self._parse_flashcard_response(response_text)
            if len(flashcards) > count:
                flashcards = flashcards[:count]
            elif len(flashcards) < count:
                logger.warning("Generated %s flashcards, expected %s.", len(flashcards), count)
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
        sections = re.split(r"\n\s*---\s*\n|\n\n+", response_text)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Look for Q: ... A: ... pattern
            q_match = re.search(r"Q:\s*(.+?)(?=A:|$)", section, re.DOTALL | re.IGNORECASE)
            a_match = re.search(r"A:\s*(.+?)(?=Q:|$)", section, re.DOTALL | re.IGNORECASE)

            if q_match and a_match:
                question = q_match.group(1).strip()
                answer = a_match.group(1).strip()

                # Clean up the text (remove extra whitespace, line breaks)
                question = " ".join(question.split())
                answer = " ".join(answer.split())

                if question and answer:
                    flashcards.append(
                        {
                            "front": question,
                            "back": answer,
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
