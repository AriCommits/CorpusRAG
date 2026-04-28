"""Profile-based tool registration for MCP server."""

from mcp.server.fastmcp import FastMCP
from config.base import BaseConfig
from db.base import DatabaseBackend
from .tools import dev as dev_tools
from .tools import learn as learn_tools

VALID_PROFILES = ("dev", "learn", "full")


def register_dev_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend, store=None) -> None:
    import time

    @mcp.tool()
    def rag_ingest(path: str, collection: str) -> dict:
        """Ingest documents into a RAG collection."""
        start = time.perf_counter()
        result = dev_tools.rag_ingest(path, collection, config, db)
        if store:
            store.log("rag_ingest", (time.perf_counter() - start) * 1000,
                      input_size=len(path), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def rag_query(collection: str, query: str, top_k: int = 5) -> dict:
        """Query a RAG collection and generate a response."""
        start = time.perf_counter()
        result = dev_tools.rag_query(collection, query, top_k, config, db)
        if store:
            store.log("rag_query", (time.perf_counter() - start) * 1000,
                      input_size=len(query), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def rag_retrieve(collection: str, query: str, top_k: int = 5) -> dict:
        """Retrieve relevant chunks without generating a response."""
        start = time.perf_counter()
        result = dev_tools.rag_retrieve(collection, query, top_k, config, db)
        if store:
            store.log("rag_retrieve", (time.perf_counter() - start) * 1000,
                      input_size=len(query), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def store_text(text: str, collection: str, metadata: dict | None = None) -> dict:
        """Store text directly into a RAG collection for later retrieval."""
        start = time.perf_counter()
        result = dev_tools.store_text(text, collection, config, db, metadata)
        if store:
            store.log("store_text", (time.perf_counter() - start) * 1000,
                      input_size=len(text), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def list_collections() -> dict:
        """List all available RAG collections."""
        start = time.perf_counter()
        result = dev_tools.list_collections(db)
        if store:
            store.log("list_collections", (time.perf_counter() - start) * 1000,
                      success=result.get("status") == "success")
        return result

    @mcp.tool()
    def collection_info(collection_name: str) -> dict:
        """Get information about a specific collection."""
        start = time.perf_counter()
        result = dev_tools.collection_info(collection_name, db)
        if store:
            store.log("collection_info", (time.perf_counter() - start) * 1000,
                      input_size=len(collection_name), success=result.get("status") == "success")
        return result

    @mcp.resource("collections://list")
    def dev_list_collections_resource() -> str:
        result = dev_tools.list_collections(db)
        collections = result.get("collections", [])
        return "\n".join(f"- {c}" for c in collections) if collections else "No collections."

    @mcp.tool()
    def get_estimate(tool_name: str) -> dict:
        """Get historical time estimate for a tool based on past execution data.

        Returns avg/p50/p95 execution times. Use this for data-backed time estimates.

        Args:
            tool_name: Name of the tool (e.g., 'rag_query', 'rag_ingest', 'store_text').
        """
        return dev_tools.get_estimate(tool_name, store)

    @mcp.tool()
    def query_telemetry(sql: str) -> dict:
        """Query the telemetry database with read-only SQL.

        Only SELECT statements are allowed. Returns rows as list of dicts.

        Args:
            sql: SQL SELECT query (e.g., 'SELECT tool_name, AVG(duration_ms) FROM tool_executions GROUP BY tool_name').
        """
        return dev_tools.query_telemetry(sql, store)


def register_learn_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend, store=None) -> None:
    import time

    @mcp.tool()
    def generate_flashcards(collection: str, count: int = 10, difficulty: str = "medium") -> dict:
        """Generate flashcards from a collection."""
        start = time.perf_counter()
        result = learn_tools.generate_flashcards(collection, count, difficulty, config, db)
        if store:
            store.log("generate_flashcards", (time.perf_counter() - start) * 1000,
                      input_size=len(collection), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def generate_summary(collection: str, topic: str | None = None, length: str = "medium") -> dict:
        """Generate a summary from a collection."""
        start = time.perf_counter()
        result = learn_tools.generate_summary(collection, topic, length, config, db)
        if store:
            store.log("generate_summary", (time.perf_counter() - start) * 1000,
                      input_size=len(collection), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def generate_quiz(collection: str, count: int = 10, question_types: list[str] | None = None) -> dict:
        """Generate a quiz from a collection."""
        start = time.perf_counter()
        result = learn_tools.generate_quiz(collection, count, question_types, config, db)
        if store:
            store.log("generate_quiz", (time.perf_counter() - start) * 1000,
                      input_size=len(collection), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def transcribe_video(video_path: str, collection: str, model: str = "base") -> dict:
        """Transcribe a video file."""
        start = time.perf_counter()
        result = learn_tools.transcribe_video(video_path, collection, model, config, db)
        if store:
            store.log("transcribe_video", (time.perf_counter() - start) * 1000,
                      input_size=len(video_path), success=result.get("status") == "success")
        return result

    @mcp.tool()
    def clean_transcript(transcript_text: str, model: str | None = None) -> dict:
        """Clean and format a transcript."""
        start = time.perf_counter()
        result = learn_tools.clean_transcript(transcript_text, model, config)
        if store:
            store.log("clean_transcript", (time.perf_counter() - start) * 1000,
                      input_size=len(transcript_text), success=result.get("status") == "success")
        return result

    @mcp.prompt()
    def study_session_prompt(collection: str, topic: str) -> str:
        return f'Study "{collection}" about "{topic}".\n1. generate_summary\n2. generate_flashcards\n3. generate_quiz'


def register_profile(mcp: FastMCP, profile: str, config: BaseConfig, db: DatabaseBackend, store=None) -> None:
    if profile not in VALID_PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {VALID_PROFILES}")
    if profile in ("dev", "full"):
        register_dev_tools(mcp, config, db, store)
    if profile in ("learn", "full"):
        register_learn_tools(mcp, config, db, store)
