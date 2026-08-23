"""Profile-based tool registration for MCP server."""

from mcp.server.fastmcp import FastMCP

from config.base import BaseConfig
from db.base import DatabaseBackend

from .telemetry import log_tool
from .tools import dev as dev_tools
from .tools import learn as learn_tools
from .tools import video as video_tools

VALID_PROFILES = ("dev", "learn", "full")


def register_dev_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend, store=None) -> None:
    @mcp.tool()
    def rag_ingest(path: str, collection: str) -> dict:
        """Ingest documents into a RAG collection."""
        return log_tool(
            store,
            "rag_ingest",
            lambda: dev_tools.rag_ingest(path, collection, config, db),
            input_size=len(path),
        )

    @mcp.tool()
    def rag_query(collection: str, query: str, top_k: int = 5) -> dict:
        """Query a RAG collection and generate a response."""
        return log_tool(
            store,
            "rag_query",
            lambda: dev_tools.rag_query(collection, query, top_k, config, db),
            input_size=len(query),
        )

    @mcp.tool()
    def rag_retrieve(collection: str, query: str, top_k: int = 5) -> dict:
        """Retrieve relevant chunks without generating a response."""
        return log_tool(
            store,
            "rag_retrieve",
            lambda: dev_tools.rag_retrieve(collection, query, top_k, config, db),
            input_size=len(query),
        )

    @mcp.tool()
    def store_text(text: str, collection: str, metadata: dict | None = None) -> dict:
        """Store text directly into a RAG collection for later retrieval."""
        return log_tool(
            store,
            "store_text",
            lambda: dev_tools.store_text(text, collection, config, db, metadata),
            input_size=len(text),
        )

    @mcp.tool()
    def list_collections() -> dict:
        """List all available RAG collections."""
        return log_tool(store, "list_collections", lambda: dev_tools.list_collections(db))

    @mcp.tool()
    def collection_info(collection_name: str) -> dict:
        """Get information about a specific collection."""
        return log_tool(
            store,
            "collection_info",
            lambda: dev_tools.collection_info(collection_name, db),
            input_size=len(collection_name),
        )

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
    @mcp.tool()
    def generate_flashcards(collection: str, count: int = 10, difficulty: str = "medium") -> dict:
        """Generate flashcards from a collection."""
        return log_tool(
            store,
            "generate_flashcards",
            lambda: learn_tools.generate_flashcards(collection, count, difficulty, config, db),
            input_size=len(collection),
        )

    @mcp.tool()
    def generate_summary(collection: str, topic: str | None = None, length: str = "medium") -> dict:
        """Generate a summary from a collection."""
        return log_tool(
            store,
            "generate_summary",
            lambda: learn_tools.generate_summary(collection, topic, length, config, db),
            input_size=len(collection),
        )

    @mcp.tool()
    def generate_quiz(
        collection: str, count: int = 10, question_types: list[str] | None = None
    ) -> dict:
        """Generate a quiz from a collection."""
        return log_tool(
            store,
            "generate_quiz",
            lambda: learn_tools.generate_quiz(collection, count, question_types, config, db),
            input_size=len(collection),
        )

    @mcp.tool()
    def transcribe_video(video_path: str, collection: str, model: str = "base") -> dict:
        """Transcribe a video file."""
        return log_tool(
            store,
            "transcribe_video",
            lambda: learn_tools.transcribe_video(video_path, collection, model, config, db),
            input_size=len(video_path),
        )

    @mcp.tool()
    def clean_transcript(transcript_text: str, model: str | None = None) -> dict:
        """Clean and format a transcript."""
        return log_tool(
            store,
            "clean_transcript",
            lambda: learn_tools.clean_transcript(transcript_text, model, config),
            input_size=len(transcript_text),
        )

    register_video_tools(mcp, config, db, store)

    @mcp.prompt()
    def study_session_prompt(collection: str, topic: str) -> str:
        return f'Study "{collection}" about "{topic}".\n1. generate_summary\n2. generate_flashcards\n3. generate_quiz'


def register_video_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend, store=None) -> None:
    from tools.video.config import VideoConfig
    from tools.video.jobs import get_job_manager

    video_config = VideoConfig.from_dict(config.raw or config.to_dict())
    job_mgr = get_job_manager(
        max_workers=video_config.max_concurrent_jobs,
        expiry_seconds=video_config.job_expiry_seconds,
    )

    @mcp.tool()
    def video_ingest_local(
        path: str,
        collection: str,
        vision_model: str | None = None,
        scene_threshold: float | None = None,
    ) -> dict:
        """Ingest a local video file using visual OCR. Returns a job_id for async tracking."""
        return log_tool(
            store,
            "video_ingest_local",
            lambda: video_tools.video_ingest_local(
                path, collection, config, db, job_mgr, vision_model, scene_threshold
            ),
            input_size=len(path),
        )

    @mcp.tool()
    def video_ingest_url(
        url: str,
        collection: str,
        vision_model: str | None = None,
        scene_threshold: float | None = None,
    ) -> dict:
        """Download a video from URL and ingest using visual OCR. Returns a job_id."""
        return log_tool(
            store,
            "video_ingest_url",
            lambda: video_tools.video_ingest_url(
                url, collection, config, db, job_mgr, vision_model, scene_threshold
            ),
            input_size=len(url),
        )

    @mcp.tool()
    def video_combined_pipeline(
        path_or_url: str,
        collection: str,
        include_audio: bool = True,
        include_visual: bool = True,
    ) -> dict:
        """Run combined audio transcription + visual OCR pipeline. Returns a job_id."""
        return log_tool(
            store,
            "video_combined_pipeline",
            lambda: video_tools.video_combined_pipeline(
                path_or_url, collection, config, db, job_mgr, include_audio, include_visual
            ),
            input_size=len(path_or_url),
        )

    @mcp.tool()
    def video_job_status(job_id: str) -> dict:
        """Check the status of a video processing job."""
        return video_tools.video_job_status(job_id, job_mgr)

    @mcp.tool()
    def video_list_jobs() -> dict:
        """List all video processing jobs and their status."""
        return video_tools.video_list_jobs(job_mgr)


def register_profile(
    mcp: FastMCP, profile: str, config: BaseConfig, db: DatabaseBackend, store=None
) -> None:
    if profile not in VALID_PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {VALID_PROFILES}")
    if profile in ("dev", "full"):
        register_dev_tools(mcp, config, db, store)
    if profile in ("learn", "full"):
        register_learn_tools(mcp, config, db, store)
