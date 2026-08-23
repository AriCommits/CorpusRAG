"""Summary generation logic."""

import logging
from typing import Any

from db import DatabaseBackend
from llm import PromptTemplates
from tools.generation import complete_prompt, sample_documents

from .config import SummaryConfig

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Generate summaries from documents in a collection."""

    def __init__(self, config: SummaryConfig, db: DatabaseBackend):
        """Initialize summary generator.

        Args:
            config: Summary configuration
            db: Database backend
        """
        self.config = config
        self.db = db

    def generate(self, collection: str, topic: str | None = None) -> dict[str, Any]:
        """Generate summary from collection.

        Args:
            collection: Collection name
            topic: Optional specific topic to summarize

        Returns:
            Summary dict with 'summary', 'keywords', and 'outline' keys
        """
        query_text = topic or "overview summary main points key concepts"
        document_texts = sample_documents(
            self.db,
            self.config,
            collection,
            query_text=query_text,
            n_results=20,
        )

        # Generate summary using LLM
        summary_text = self._generate_with_llm(
            document_texts, length=self.config.summary_length, topic=topic
        )

        # Build result dict
        result: dict[str, Any] = {
            "summary": summary_text,
            "collection": collection,
        }

        # Generate additional components if requested
        if self.config.include_keywords:
            result["keywords"] = self._extract_keywords(summary_text, document_texts)

        if self.config.include_outline:
            result["outline"] = self._generate_outline(summary_text)

        return result

    def _generate_with_llm(
        self,
        documents: list[str],
        length: str,
        topic: str | None = None,
    ) -> str:
        """Generate summary using LLM.

        Args:
            documents: List of document texts
            length: Summary length (short, medium, long)
            topic: Optional topic for focused generation

        Returns:
            Generated summary text
        """
        # Create prompt using template
        prompt = PromptTemplates.summary_generation(
            documents=documents,
            length=length,
            topic=topic,
        )

        try:
            return complete_prompt(self.config, prompt)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error generating summary: {e}"

    def _extract_keywords(self, summary_text: str, document_texts: list[str]) -> list[str]:
        """Extract keywords from summary and documents.

        Args:
            summary_text: Generated summary
            document_texts: Original documents

        Returns:
            List of keywords
        """
        try:
            # Simple keyword extraction prompt
            keyword_prompt = f"""Extract 8-12 key terms and concepts from the following summary and content.

SUMMARY:
{summary_text}

INSTRUCTIONS:
- Extract important terms, concepts, names, and topics
- Focus on substantive words, not common terms
- Return as a simple comma-separated list
- No explanations, just the keywords

KEYWORDS:"""

            keywords_text = complete_prompt(self.config, keyword_prompt)
            keywords = [kw.strip() for kw in keywords_text.split(",")]

            # Clean and filter keywords
            keywords = [kw for kw in keywords if kw and len(kw) > 2]

            return keywords[:12]  # Limit to 12 keywords

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return ["summary", "overview", "key points"]

    def _generate_outline(self, summary_text: str) -> list[str]:
        """Generate an outline from the summary.

        Args:
            summary_text: Generated summary

        Returns:
            List of outline points
        """
        try:
            # Generate outline prompt
            outline_prompt = f"""Create a clear, hierarchical outline for the following summary.

SUMMARY:
{summary_text}

INSTRUCTIONS:
- Use Roman numerals for main sections (I, II, III, etc.)
- Use capital letters for subsections (A, B, C, etc.)
- Use numbers for detailed points (1, 2, 3, etc.)
- Keep it concise but comprehensive
- Focus on logical structure and flow

OUTLINE:"""

            outline_text = complete_prompt(self.config, outline_prompt)

            # Split into lines and clean up
            outline_lines = [line.strip() for line in outline_text.split("\n")]
            outline_lines = [
                line for line in outline_lines if line and not line.lower().startswith("outline")
            ]

            return outline_lines[:15]  # Limit to reasonable length

        except Exception as e:
            logger.error(f"Error generating outline: {e}")
            return [
                "I. Introduction",
                "II. Main Points",
                "III. Key Concepts",
                "IV. Conclusion",
            ]

    def format_summary(self, summary: dict[str, Any]) -> str:
        """Format summary as markdown.

        Args:
            summary: Summary dict

        Returns:
            Formatted summary string
        """
        lines = [f"# Summary: {summary['collection']}", ""]

        if "keywords" in summary and self.config.include_keywords:
            lines.append("## Keywords")
            keywords = summary.get("keywords", [])
            lines.extend([f"- {kw}" for kw in keywords])
            lines.append("")

        if "outline" in summary and self.config.include_outline:
            lines.append("## Outline")
            outline = summary.get("outline", [])
            lines.extend(outline)
            lines.append("")

        lines.append("## Summary")
        lines.append(str(summary["summary"]))

        return "\n".join(lines)
