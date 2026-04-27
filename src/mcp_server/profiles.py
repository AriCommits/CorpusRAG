"""Profile-based tool registration for MCP server."""

from mcp.server.fastmcp import FastMCP
from config.base import BaseConfig
from db.base import DatabaseBackend
from .tools import dev as dev_tools
from .tools import learn as learn_tools

VALID_PROFILES = ("dev", "learn", "full")


def register_dev_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend) -> None:
    @mcp.tool()
    def rag_ingest(path: str, collection: str) -> dict:
        """Ingest documents into a RAG collection."""
        return dev_tools.rag_ingest(path, collection, config, db)

    @mcp.tool()
    def rag_query(collection: str, query: str, top_k: int = 5) -> dict:
        """Query a RAG collection and generate a response."""
        return dev_tools.rag_query(collection, query, top_k, config, db)

    @mcp.tool()
    def rag_retrieve(collection: str, query: str, top_k: int = 5) -> dict:
        """Retrieve relevant chunks without generating a response."""
        return dev_tools.rag_retrieve(collection, query, top_k, config, db)

    @mcp.tool()
    def store_text(text: str, collection: str, metadata: dict | None = None) -> dict:
        """Store text directly into a RAG collection for later retrieval."""
        return dev_tools.store_text(text, collection, config, db, metadata)

    @mcp.tool()
    def list_collections() -> dict:
        """List all available RAG collections."""
        return dev_tools.list_collections(db)

    @mcp.tool()
    def collection_info(collection_name: str) -> dict:
        """Get information about a specific collection."""
        return dev_tools.collection_info(collection_name, db)

    @mcp.resource("collections://list")
    def dev_list_collections_resource() -> str:
        result = dev_tools.list_collections(db)
        collections = result.get("collections", [])
        return "\n".join(f"- {c}" for c in collections) if collections else "No collections."


def register_learn_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend) -> None:
    @mcp.tool()
    def generate_flashcards(collection: str, count: int = 10, difficulty: str = "medium") -> dict:
        """Generate flashcards from a collection."""
        return learn_tools.generate_flashcards(collection, count, difficulty, config, db)

    @mcp.tool()
    def generate_summary(collection: str, topic: str | None = None, length: str = "medium") -> dict:
        """Generate a summary from a collection."""
        return learn_tools.generate_summary(collection, topic, length, config, db)

    @mcp.tool()
    def generate_quiz(collection: str, count: int = 10, question_types: list[str] | None = None) -> dict:
        """Generate a quiz from a collection."""
        return learn_tools.generate_quiz(collection, count, question_types, config, db)

    @mcp.tool()
    def transcribe_video(video_path: str, collection: str, model: str = "base") -> dict:
        """Transcribe a video file."""
        return learn_tools.transcribe_video(video_path, collection, model, config, db)

    @mcp.tool()
    def clean_transcript(transcript_text: str, model: str | None = None) -> dict:
        """Clean and format a transcript."""
        return learn_tools.clean_transcript(transcript_text, model, config)

    @mcp.prompt()
    def study_session_prompt(collection: str, topic: str) -> str:
        return f'Study "{collection}" about "{topic}".\n1. generate_summary\n2. generate_flashcards\n3. generate_quiz'


def register_profile(mcp: FastMCP, profile: str, config: BaseConfig, db: DatabaseBackend) -> None:
    if profile not in VALID_PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {VALID_PROFILES}")
    if profile in ("dev", "full"):
        register_dev_tools(mcp, config, db)
    if profile in ("learn", "full"):
        register_learn_tools(mcp, config, db)
