"""
MCP Server implementation using FastMCP.

Exposes all Corpus Callosum tools as MCP resources and tools.
"""

import argparse
import logging
from typing import Any

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from corpus_callosum.config import load_config
from corpus_callosum.db import ChromaDBBackend
from corpus_callosum.tools.flashcards import FlashcardConfig, FlashcardGenerator
from corpus_callosum.tools.quizzes import QuizConfig, QuizGenerator
from corpus_callosum.tools.rag import RAGAgent, RAGConfig, RAGIngester, RAGRetriever
from corpus_callosum.tools.summaries import SummaryConfig, SummaryGenerator
from corpus_callosum.tools.video import (
    TranscriptAugmenter,
    TranscriptCleaner,
    VideoConfig,
    VideoTranscriber,
)


def create_mcp_server(config_path: str | None = None) -> FastMCP:
    """
    Create and configure the MCP server with all Corpus Callosum tools.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configured FastMCP server instance
    """
    # Load configuration
    config = load_config(config_path)

    # Initialize database backend
    db = ChromaDBBackend(config.database)

    # Create MCP server
    mcp = FastMCP(
        "Corpus Callosum",
        json_response=True,
    )

    # ==================== RAG Tools ====================

    @mcp.tool()
    def rag_ingest(
        path: str,
        collection: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> dict[str, Any]:
        """
        Ingest documents into a RAG collection.

        Args:
            path: Path to file or directory to ingest
            collection: Collection name to store documents
            chunk_size: Size of text chunks (default: 1000)
            chunk_overlap: Overlap between chunks (default: 200)

        Returns:
            Ingestion result with document count and status
        """
        rag_config = RAGConfig.from_dict(config.to_dict())
        rag_config.chunking.chunk_size = chunk_size
        rag_config.chunking.chunk_overlap = chunk_overlap

        ingester = RAGIngester(rag_config, db)
        result = ingester.ingest_path(path, collection)

        return {
            "status": "success",
            "collection": collection,
            "documents_processed": result.documents_processed,
            "chunks_created": result.chunks_created,
        }

    @mcp.tool()
    def rag_query(
        collection: str,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Query a RAG collection and generate a response.

        Args:
            collection: Collection name to query
            query: Question or query text
            top_k: Number of chunks to retrieve (default: 5)

        Returns:
            Generated response with source chunks
        """
        rag_config = RAGConfig.from_dict(config.to_dict())
        rag_config.retrieval.top_k = top_k

        agent = RAGAgent(rag_config, db)
        response = agent.query(query, collection)

        return {
            "status": "success",
            "query": query,
            "response": response,
        }

    @mcp.tool()
    def rag_retrieve(
        collection: str,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Retrieve relevant chunks from a RAG collection without generating a response.

        Args:
            collection: Collection name to query
            query: Search query text
            top_k: Number of chunks to retrieve (default: 5)

        Returns:
            List of retrieved chunks with metadata
        """
        rag_config = RAGConfig.from_dict(config.to_dict())
        rag_config.retrieval.top_k = top_k

        retriever = RAGRetriever(rag_config, db)
        chunks = retriever.retrieve(collection, query)

        return {
            "status": "success",
            "query": query,
            "chunks": [
                {
                    "text": chunk.text,
                    "source": chunk.metadata.get("source", ""),
                    "score": chunk.score,
                }
                for chunk in chunks
            ],
        }

    # ==================== Flashcard Tools ====================

    @mcp.tool()
    def generate_flashcards(
        collection: str,
        count: int = 10,
        difficulty: str = "medium",
        output_format: str = "plain",
    ) -> dict[str, Any]:
        """
        Generate flashcards from a collection.

        Args:
            collection: Collection name containing study material
            count: Number of flashcards to generate (default: 10)
            difficulty: Difficulty level (easy/medium/hard, default: medium)
            output_format: Output format (plain/anki/quizlet, default: plain)

        Returns:
            Generated flashcards in requested format
        """
        flashcard_config = FlashcardConfig.from_dict(config.to_dict())
        flashcard_config.cards_per_topic = count
        flashcard_config.difficulty_levels = [difficulty]
        flashcard_config.format = output_format

        generator = FlashcardGenerator(flashcard_config, db)
        flashcards = generator.generate(collection)

        return {
            "status": "success",
            "collection": collection,
            "count": len(flashcards),
            "flashcards": flashcards,
        }

    # ==================== Summary Tools ====================

    @mcp.tool()
    def generate_summary(
        collection: str,
        topic: str | None = None,
        length: str = "medium",
        include_keywords: bool = True,
        include_outline: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a summary from a collection.

        Args:
            collection: Collection name containing material to summarize
            topic: Optional specific topic to focus on
            length: Summary length (short/medium/long, default: medium)
            include_keywords: Include key terms (default: True)
            include_outline: Include outline structure (default: False)

        Returns:
            Generated summary with optional keywords and outline
        """
        summary_config = SummaryConfig.from_dict(config.to_dict())
        summary_config.summary_length = length
        summary_config.include_keywords = include_keywords
        summary_config.include_outline = include_outline

        generator = SummaryGenerator(summary_config, db)
        summary = generator.generate(collection, topic)

        return {
            "status": "success",
            "collection": collection,
            "topic": topic,
            "summary": summary,
        }

    # ==================== Quiz Tools ====================

    @mcp.tool()
    def generate_quiz(
        collection: str,
        count: int = 10,
        question_types: list[str] | None = None,
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """
        Generate a quiz from a collection.

        Args:
            collection: Collection name containing quiz material
            count: Number of questions to generate (default: 10)
            question_types: Types of questions (multiple_choice/true_false/short_answer)
            output_format: Output format (markdown/json/csv, default: markdown)

        Returns:
            Generated quiz in requested format
        """
        quiz_config = QuizConfig.from_dict(config.to_dict())
        quiz_config.questions_per_topic = count
        if question_types:
            quiz_config.question_types = question_types
        quiz_config.format = output_format

        generator = QuizGenerator(quiz_config, db)
        quiz = generator.generate(collection)

        return {
            "status": "success",
            "collection": collection,
            "count": count,
            "quiz": quiz,
        }

    # ==================== Video Tools ====================

    @mcp.tool()
    def transcribe_video(
        video_path: str,
        collection: str,
        model: str = "base",
    ) -> dict[str, Any]:
        """
        Transcribe a video file using Whisper.

        Args:
            video_path: Path to video file
            collection: Collection name to store transcript
            model: Whisper model size (tiny/base/small/medium/large, default: base)

        Returns:
            Transcription result with text and metadata
        """
        video_config = VideoConfig.from_dict(config.to_dict())
        video_config.whisper.model = model

        transcriber = VideoTranscriber(video_config, db)
        transcript = transcriber.transcribe_file(video_path, collection)

        return {
            "status": "success",
            "video_path": video_path,
            "collection": collection,
            "transcript": transcript,
        }

    @mcp.tool()
    def clean_transcript(
        transcript_text: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Clean and format a transcript using LLM.

        Args:
            transcript_text: Raw transcript text to clean
            model: Optional LLM model to use for cleaning

        Returns:
            Cleaned transcript text
        """
        video_config = VideoConfig.from_dict(config.to_dict())
        if model:
            video_config.ollama_cleaning.model = model

        cleaner = TranscriptCleaner(video_config)
        cleaned = cleaner.clean(transcript_text)

        return {
            "status": "success",
            "cleaned_transcript": cleaned,
        }

    # ==================== Resource: Collections ====================

    @mcp.resource("collections://list")
    def list_collections() -> str:
        """List all available collections in the database."""
        collections = db.list_collections()
        return "\n".join([f"- {col.name}" for col in collections])

    @mcp.resource("collection://{collection_name}")
    def get_collection_info(collection_name: str) -> str:
        """Get information about a specific collection."""
        collection = db.get_collection(collection_name)
        count = collection.count()
        return f"Collection: {collection_name}\nDocument count: {count}"

    # ==================== Prompts ====================

    @mcp.prompt()
    def study_session_prompt(collection: str, topic: str) -> str:
        """Generate a prompt for a comprehensive study session."""
        return f"""Please help me study the topic "{topic}" from the collection "{collection}".

I would like you to:
1. Provide a clear summary of the main concepts
2. Generate flashcards for key terms and concepts
3. Create a quiz to test my understanding

Use the following tools in sequence:
- generate_summary(collection="{collection}", topic="{topic}")
- generate_flashcards(collection="{collection}", count=15)
- generate_quiz(collection="{collection}", count=10)
"""

    @mcp.prompt()
    def lecture_processing_prompt(video_path: str, course: str) -> str:
        """Generate a prompt for processing a lecture video."""
        return f"""Please process the lecture video at "{video_path}" for course "{course}".

Steps:
1. Transcribe the video using transcribe_video()
2. Clean the transcript using clean_transcript()
3. Ingest the transcript into a RAG collection
4. Generate study materials (summary, flashcards, quiz)

This will create a comprehensive study resource from the lecture.
"""

    return mcp


def main() -> None:
    """Run the MCP server with optional HTTP health endpoints."""
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Corpus Callosum MCP Server")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--transport", default="streamable-http", help="Transport type")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create MCP server
    mcp = create_mcp_server(args.config)
    
    # Add health endpoints to the underlying FastAPI app
    if hasattr(mcp, 'app') and isinstance(mcp.app, FastAPI):
        @mcp.app.get("/health")
        async def health_check():
            """Health check endpoint for container orchestration."""
            return {
                "status": "healthy",
                "service": "corpus-callosum-mcp",
                "version": "0.5.0",
                "timestamp": "2026-04-07"
            }
        
        @mcp.app.get("/health/ready")  
        async def readiness_check():
            """Readiness check endpoint."""
            try:
                # Test database connection
                from corpus_callosum.config import load_config
                from corpus_callosum.db import ChromaDBBackend
                
                config = load_config(args.config)
                db = ChromaDBBackend(config.database)
                collections = db.list_collections()
                
                return {
                    "status": "ready",
                    "database": "connected",
                    "collections": len(collections)
                }
            except Exception as e:
                logger.error(f"Readiness check failed: {e}")
                return {"status": "not_ready", "error": str(e)}

    logger.info(f"Starting Corpus Callosum MCP Server on {args.host}:{args.port}")
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
