"""Developer-focused MCP tool functions for CorpusRAG."""

from typing import Any

from config.base import BaseConfig
from db.base import DatabaseBackend
from tools.rag import RAGRetriever
from tools.rag.config import RAGConfig
from utils.security import validate_file_path
from utils.validation import get_validator


def rag_ingest(
    path: str, collection: str, config: BaseConfig, db: DatabaseBackend
) -> dict[str, Any]:
    """Ingest documents from a path into a RAG collection."""
    try:
        validated_path = validate_file_path(
            path, must_exist=True, allowed_roots=[str(config.paths.vault)]
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        from kernel import Corpus

        corpus = Corpus.from_loaded(config, db)
        result = corpus.ingest_path(str(validated_path), collection)
        return {
            "status": "success",
            "collection": collection,
            "files_indexed": result.files_indexed,
            "chunks_indexed": result.chunks_indexed,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def rag_query(
    collection: str, query: str, top_k: int, config: BaseConfig, db: DatabaseBackend
) -> dict[str, Any]:
    """Query a RAG collection and generate a response."""
    validator = get_validator()
    try:
        validated_query = validator.validate_query(query)
        validated_top_k = validator.validate_top_k(top_k, min_val=1, max_val=100)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        from kernel import Corpus

        corpus = Corpus.from_loaded(config, db)
        response = corpus.ask(validated_query, collection, top_k=validated_top_k)
        return {"status": "success", "query": query, "response": response}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def rag_retrieve(
    collection: str, query: str, top_k: int, config: BaseConfig, db: DatabaseBackend
) -> dict[str, Any]:
    """Retrieve relevant chunks from a RAG collection without generating a response."""
    validator = get_validator()
    try:
        validated_query = validator.validate_query(query)
        validated_top_k = validator.validate_top_k(top_k, min_val=1, max_val=100)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        rag_config = RAGConfig.from_dict(config.raw or config.to_dict())
        retriever = RAGRetriever(rag_config, db)
        chunks = retriever.retrieve(validated_query, collection, top_k=validated_top_k)
        return {
            "status": "success",
            "query": query,
            "chunks": [
                {
                    "text": c.text,
                    "source": c.metadata.get("source", ""),
                    "score": c.score,
                }
                for c in chunks
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def store_text(
    text: str,
    collection: str,
    config: BaseConfig,
    db: DatabaseBackend,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Store raw text directly into a RAG collection."""
    try:
        if len(text) > 100_000:
            return {"status": "error", "error": "Text too large (max 100KB)"}
        _ALLOWED_META = {"topic", "tags", "author", "date", "notes", "source"}
        safe_meta = {"source_type": "agent_text"}
        if metadata:
            safe_meta.update({k: v for k, v in metadata.items() if k in _ALLOWED_META})

        from kernel import Corpus

        corpus = Corpus.from_loaded(config, db)
        result = corpus.ingest_text(text, collection, metadata=safe_meta)
        return {
            "status": "success",
            "collection": collection,
            "chunks_created": result.chunks_indexed,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def list_collections(db: DatabaseBackend) -> dict[str, Any]:
    """List all collections in the database."""
    collections = db.list_collections()
    return {"status": "success", "collections": collections}


def collection_info(collection_name: str, db: DatabaseBackend) -> dict[str, Any]:
    """Get statistics for a collection."""
    try:
        stats = db.get_collection_stats(collection_name)
        return {"status": "success", **stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_estimate(tool_name: str, store) -> dict[str, Any]:
    """Get time estimate for a tool based on historical execution data."""
    if not store:
        return {"status": "error", "error": "Telemetry is disabled"}
    try:
        estimates = store.get_estimates(tool_name)
        if not estimates:
            return {
                "status": "success",
                "tool": tool_name,
                "estimate": None,
                "message": f"No historical data for '{tool_name}'",
            }
        return {"status": "success", **estimates}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def query_telemetry(sql: str, store) -> dict[str, Any]:
    """Execute a read-only SQL query against the telemetry database."""
    if not store:
        return {"status": "error", "error": "Telemetry is disabled"}
    try:
        rows = store.query(sql)
        return {"status": "success", "rows": rows, "count": len(rows)}
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
