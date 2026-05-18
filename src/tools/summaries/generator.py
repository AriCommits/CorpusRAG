"""Summary generation logic."""

import logging
from typing import Any

from db import DatabaseBackend
from llm import PromptTemplates, create_backend
from tools.rag.embeddings import EmbeddingClient

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

    def generate(self, collection: str, topic: str | None = None) -> dict[str, Any]:
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

        # Get document count to determine sampling strategy
        doc_count = self.db.count_documents(full_collection)

        if doc_count == 0:
            raise ValueError(
                f"No documents found in '{full_collection}'. "
                f"Run: corpus rag ingest --collection {collection}"
            )

        # Get a representative sample of documents
        # For summary, we want broader coverage than specific search
        sample_size = min(20, max(5, doc_count // 10))  # 10% of docs, between 5-20

        # Get documents by querying for general terms or using pagination
        document_texts = self._get_representative_documents(full_collection, sample_size, topic)

        if not document_texts:
            raise ValueError(
                f"Could not retrieve documents from '{full_collection}'. "
                f"Run: corpus rag ingest --collection {collection}"
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

    def _get_representative_documents(
        self, full_collection: str, sample_size: int, topic: str | None = None
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
            # Use semantic search to get relevant documents
            embedder = EmbeddingClient(self.config)

            # Use topic if provided, otherwise use general query
            if topic:
                query_text = topic
            else:
                query_text = "overview summary main points key concepts"

            query_embedding = embedder.embed_query(query_text)

            results = self.db.query(
                collection=full_collection,
                query_embedding=query_embedding,
                n_results=sample_size,
            )

            documents = results.get("documents", [[]])[0]
            return documents if documents else []

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

            response = self.llm_backend.complete(outline_prompt)

            # Split into lines and clean up
            outline_lines = [line.strip() for line in response.text.split("\n")]
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
