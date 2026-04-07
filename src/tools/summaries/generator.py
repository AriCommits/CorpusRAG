"""Summary generation logic."""

import logging
import re
from typing import Any, Optional

from corpus_callosum.db import DatabaseBackend
from corpus_callosum.llm import create_backend, PromptTemplates

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
        # Create LLM backend for generation
        self.llm_backend = create_backend(config.llm.to_backend_config())

    def generate(self, collection: str, topic: Optional[str] = None) -> dict[str, Any]:
        """Generate summary from collection.

        Args:
            collection: Collection name
            topic: Optional specific topic to summarize

        Returns:
            Summary dict with 'summary', 'keywords', and 'outline' keys
        """
        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Check if collection exists
        if not self.db.collection_exists(full_collection):
            raise ValueError(f"Collection '{full_collection}' does not exist")

        try:
            # Get document count to determine sampling strategy
            doc_count = self.db.count_documents(full_collection)
            
            if doc_count == 0:
                logger.warning(f"No documents found in collection '{full_collection}'")
                return self._generate_placeholder_summary(collection, topic)
            
            # Get a representative sample of documents
            # For summary, we want broader coverage than specific search
            sample_size = min(20, max(5, doc_count // 10))  # 10% of docs, between 5-20
            
            # Get documents by querying for general terms or using pagination
            document_texts = self._get_representative_documents(full_collection, sample_size, topic)
            
            if not document_texts:
                logger.warning(f"Could not retrieve documents from '{full_collection}'")
                return self._generate_placeholder_summary(collection, topic)
            
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
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fall back to placeholder summary
            return self._generate_placeholder_summary(collection, topic)

    def _get_representative_documents(
        self, full_collection: str, sample_size: int, topic: Optional[str] = None
    ) -> list[str]:
        """Get representative documents from collection.
        
        Args:
            full_collection: Full collection name with prefix
            sample_size: Number of documents to sample
            topic: Optional topic to focus on
            
        Returns:
            List of document texts
        """
        try:
            # For now, use a simple approach - get all documents and sample
            # In a real implementation, you'd want smarter sampling
            
            # Get collection object to access documents directly
            collection_obj = self.db.get_collection(full_collection)
            
            # This is a simplified approach - in practice you'd implement
            # better document sampling or use the collection's get() method
            # with limit and offset for pagination
            
            # For now, return placeholder approach
            # TODO: Implement proper document sampling based on the actual database backend
            return [
                f"Sample document from {full_collection}",
                f"Another sample document from {full_collection}",
                f"Topic-related content for {topic or 'general content'}",
            ]
            
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

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
            # Generate content using LLM
            response = self.llm_backend.complete(prompt)
            return response.text.strip()
            
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
            
            response = self.llm_backend.complete(keyword_prompt)
            
            # Parse comma-separated keywords
            keywords_text = response.text.strip()
            keywords = [kw.strip() for kw in keywords_text.split(',')]
            
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
            
            response = self.llm_backend.complete(outline_prompt)
            
            # Split into lines and clean up
            outline_lines = [line.strip() for line in response.text.split('\n')]
            outline_lines = [line for line in outline_lines if line and not line.lower().startswith('outline')]
            
            return outline_lines[:15]  # Limit to reasonable length
            
        except Exception as e:
            logger.error(f"Error generating outline: {e}")
            return [
                "I. Introduction",
                "II. Main Points",
                "III. Key Concepts", 
                "IV. Conclusion",
            ]

    def _generate_placeholder_summary(
        self, collection: str, topic: Optional[str] = None
    ) -> dict[str, Any]:
        """Generate placeholder summary as fallback.
        
        Args:
            collection: Collection name
            topic: Optional topic
            
        Returns:
            Placeholder summary dictionary
        """
        topic_text = f" - {topic}" if topic else ""
        
        result: dict[str, Any] = {
            "summary": (
                f"Summary of {collection}{topic_text}\n\n"
                "This is a placeholder summary. Please check your LLM connection "
                "and try again for actual content generation."
            ),
            "collection": collection,
        }

        if self.config.include_keywords:
            result["keywords"] = [collection, "placeholder", "summary"]

        if self.config.include_outline:
            result["outline"] = [
                "I. Collection Overview",
                "II. Content Analysis Needed",
                "III. LLM Connection Required",
            ]

        return result

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
