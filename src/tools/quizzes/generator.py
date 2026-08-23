"""Quiz generation logic."""

import json
import logging
import re
from typing import Any

from db import DatabaseBackend
from llm import PromptTemplates
from tools.generation import complete_prompt, sample_documents

from .config import QuizConfig

logger = logging.getLogger(__name__)


class QuizGenerator:
    """Generate quizzes from documents in a collection."""

    def __init__(self, config: QuizConfig, db: DatabaseBackend):
        """Initialize quiz generator.

        Args:
            config: Quiz configuration
            db: Database backend
        """
        self.config = config
        self.db = db

    def generate(
        self,
        collection: str,
        count: int | None = None,
        difficulty: str = "intermediate",
    ) -> list[dict[str, Any]]:
        """Generate quiz questions from collection.

        Args:
            collection: Collection name
            count: Number of questions to generate (uses config default if None)
            difficulty: Difficulty level for questions

        Returns:
            List of question dicts with 'question', 'type', 'answer', 'options', 'explanation' keys
        """
        if count is None:
            count = self.config.questions_per_topic

        document_texts = sample_documents(
            self.db,
            self.config,
            collection,
            query_text="key concepts topics main ideas",
            n_results=15,
        )

        questions = self._generate_with_llm(
            document_texts, difficulty=difficulty, count=count, topic=collection
        )

        for question in questions:
            question["collection"] = collection

        if len(questions) > count:
            questions = questions[:count]
        elif len(questions) < count:
            logger.warning("Generated %s questions, expected %s.", len(questions), count)

        return questions

    def _generate_with_llm(
        self,
        documents: list[str],
        difficulty: str,
        count: int,
        topic: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate quiz questions using LLM.

        Args:
            documents: List of document texts
            difficulty: Difficulty level
            count: Number of questions to generate
            topic: Optional topic for focused generation

        Returns:
            List of question dictionaries
        """
        # Create prompt using template
        prompt = PromptTemplates.quiz_generation(
            documents=documents,
            difficulty=difficulty,
            count=count,
            topic=topic,
        )

        try:
            response_text = complete_prompt(self.config, prompt)
            questions = self._parse_quiz_response(response_text)

            return questions

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return []

    def _parse_quiz_response(self, response_text: str) -> list[dict[str, Any]]:
        """Parse LLM response into quiz question format.

        Args:
            response_text: Raw LLM response text

        Returns:
            List of question dictionaries
        """
        questions = []

        # Split response into question blocks
        question_blocks = re.split(r"\n\s*Question\s+\d+:", response_text)

        for block in question_blocks[1:]:  # Skip first empty split
            block = block.strip()
            if not block:
                continue

            try:
                question_data = self._parse_single_question(block)
                if question_data:
                    questions.append(question_data)
            except Exception as e:
                logger.warning(f"Failed to parse question block: {e}")
                continue

        return questions

    def _parse_single_question(self, block: str) -> dict[str, Any] | None:
        """Parse a single question block.

        Args:
            block: Single question text block

        Returns:
            Question dictionary or None if parsing failed
        """
        # Extract question text (first line usually)
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            return None

        question_text = lines[0]

        # Determine question type
        q_type = "short_answer"  # default
        if re.search(r"Type:\s*(Multiple Choice|True-False)", block, re.IGNORECASE):
            type_match = re.search(r"Type:\s*(\w+\s?\w*)", block, re.IGNORECASE)
            if type_match:
                q_type_raw = type_match.group(1).lower().replace(" ", "_").replace("-", "_")
                if q_type_raw in ["multiple_choice", "true_false", "short_answer"]:
                    q_type = q_type_raw

        question_data: dict[str, Any] = {
            "question": question_text,
            "type": q_type,
        }

        # Extract options for multiple choice or true/false
        if q_type == "multiple_choice":
            options = []
            for line in lines:
                if re.match(r"^[A-D]\)", line):
                    option = re.sub(r"^[A-D]\)\s*", "", line)
                    options.append(option)
            question_data["options"] = options
        elif q_type == "true_false":
            question_data["options"] = ["True", "False"]

        # Extract correct answer
        answer_match = re.search(
            r"Correct Answer:\s*(.+?)(?=\n|Explanation:|$)",
            block,
            re.IGNORECASE | re.DOTALL,
        )
        if answer_match:
            answer = answer_match.group(1).strip()
            question_data["answer"] = answer
        # Default answer based on type
        elif q_type == "multiple_choice" and question_data.get("options"):
            question_data["answer"] = question_data["options"][0]
        elif q_type == "true_false":
            question_data["answer"] = "True"
        else:
            question_data["answer"] = "Answer not provided"

        # Extract explanation if present
        if self.config.include_explanations:
            explanation_match = re.search(
                r"Explanation:\s*(.+?)(?=\n\s*Question|\n\s*$|$)",
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if explanation_match:
                explanation = explanation_match.group(1).strip()
                question_data["explanation"] = explanation

        return question_data

    def format_quiz(self, questions: list[dict[str, Any]]) -> str:
        """Format quiz questions according to config format.

        Args:
            questions: List of question dicts

        Returns:
            Formatted quiz string
        """
        if self.config.format == "markdown":
            return self._format_markdown(questions)
        elif self.config.format == "json":
            return json.dumps(questions, indent=2)
        else:  # csv
            return self._format_csv(questions)

    def _format_markdown(self, questions: list[dict[str, Any]]) -> str:
        """Format as markdown."""
        lines = ["# Quiz", ""]

        for i, q in enumerate(questions, 1):
            lines.append(f"## Question {i}")
            lines.append(f"**{q['question']}**")
            lines.append("")

            if "options" in q:
                for opt in q["options"]:
                    lines.append(f"- {opt}")
                lines.append("")

            lines.append(f"**Answer:** {q['answer']}")

            if self.config.include_explanations and "explanation" in q:
                lines.append(f"**Explanation:** {q['explanation']}")

            lines.append("")

        return "\n".join(lines)

    def _format_csv(self, questions: list[dict[str, Any]]) -> str:
        """Format as CSV."""
        lines = ["Question,Type,Answer,Options,Explanation"]

        for q in questions:
            options = "|".join(q.get("options", []))
            explanation = q.get("explanation", "")
            lines.append(
                f'"{q["question"]}",{q["type"]},"{q["answer"]}","{options}","{explanation}"'
            )

        return "\n".join(lines)
