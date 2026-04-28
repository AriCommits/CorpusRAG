"""Developer-focused MCP tool functions for CorpusRAG."""

import hashlib
from datetime import datetime
from typing import Any

from config.base import BaseConfig
from db.base import DatabaseBackend
from tools.rag import RAGAgent, RAGIngester, RAGRetriever
from tools.rag.config import RAGConfig
from tools.rag.pipeline import EmbeddingClient
from utils.security import validate_file_path
from utils.validation import get_validator


def rag_ingest(path: str, collection: str, config: BaseConfig, db: DatabaseBackend) -> dict[str, Any]:
    """Ingest documents from a path into a RAG collection."""
    try:
        validated_path = validate_file_path(path, must_exist=True)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        rag_config = RAGConfig.from_dict(config.to_dict())
        ingester = RAGIngester(rag_config, db)
        result = ingester.ingest_path(str(validated_path), collection)
        return {
            "status": "success",
            "collection": collection,
            "files_indexed": result.files_indexed,
            "chunks_indexed": result.chunks_indexed,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def rag_query(collection: str, query: str, top_k: int, config: BaseConfig, db: DatabaseBackend) -> dict[str, Any]:
    """Query a RAG collection and generate a response."""
    validator = get_validator()
    try:
        validated_query = validator.validate_query(query)
        validated_top_k = validator.validate_top_k(top_k, min_val=1, max_val=100)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        rag_config = RAGConfig.from_dict(config.to_dict())
        agent = RAGAgent(rag_config, db)
        response = agent.query(validated_query, collection, top_k=validated_top_k)
        return {"status": "success", "query": query, "response": response}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def rag_retrieve(collection: str, query: str, top_k: int, config: BaseConfig, db: DatabaseBackend) -> dict[str, Any]:
    """Retrieve relevant chunks from a RAG collection without generating a response."""
    validator = get_validator()
    try:
        validated_query = validator.validate_query(query)
        validated_top_k = validator.validate_top_k(top_k, min_val=1, max_val=100)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        rag_config = RAGConfig.from_dict(config.to_dict())
        retriever = RAGRetriever(rag_config, db)
        chunks = retriever.retrieve(validated_query, collection, top_k=validated_top_k)
        return {
            "status": "success",
            "query": query,
            "chunks": [
                {"text": c.text, "source": c.metadata.get("source", ""), "score": c.score}
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
        rag_config = RAGConfig.from_dict(config.to_dict())
        full_collection = f"{rag_config.collection_prefix}_{collection}"

        if not db.collection_exists(full_collection):
            db.create_collection(full_collection)

        from tools.rag.pipeline.adaptive_splitter import adaptive_split
        chunks = adaptive_split(text, base_chunk_size=rag_config.chunking.child_chunk_size, base_overlap=rag_config.chunking.child_chunk_overlap)

        embeddings = EmbeddingClient(rag_config).embed_texts(chunks)

        base_meta = {"source_type": "agent_text", "timestamp": datetime.now().isoformat(), "collection_name": collection}
        if metadata:
            base_meta.update(metadata)

        metadatas = [dict(base_meta) for _ in chunks]
        ids = [
            hashlib.sha256(f"{full_collection}::{i}::{chunk}".encode()).hexdigest()[:16]
            for i, chunk in enumerate(chunks)
        ]

        db.add_documents(full_collection, chunks, embeddings, metadatas, ids)
        return {"status": "success", "collection": collection, "chunks_created": len(chunks)}
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
            return {"status": "success", "tool": tool_name, "estimate": None,
                    "message": f"No historical data for '{tool_name}'"}
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