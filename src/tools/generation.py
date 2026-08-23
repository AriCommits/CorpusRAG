"""Shared helpers for collection-backed LLM generators."""

from __future__ import annotations

from db import DatabaseBackend
from llm import create_backend
from tools.rag.pipeline import EmbeddingClient

_INGEST_HINT = "Run: corpus tools rag ingest --collection {collection}"


def full_collection_name(config, collection: str) -> str:
    """Return the prefixed Chroma collection name."""
    return f"{config.collection_prefix}_{collection}"


def sample_documents(
    db: DatabaseBackend,
    config,
    collection: str,
    *,
    query_text: str,
    n_results: int,
) -> list[str]:
    """Resolve ``rag_<collection>``, require it non-empty, and sample texts."""
    full = full_collection_name(config, collection)
    if not db.collection_exists(full):
        raise ValueError(f"Collection '{full}' does not exist")

    embedder = EmbeddingClient(config)
    query_embedding = embedder.embed_query(query_text)
    results = db.query(
        collection=full,
        query_embedding=query_embedding,
        n_results=n_results,
    )
    texts = (results.get("documents") or [[]])[0] if results else []
    if not texts:
        raise ValueError(
            f"No documents found in '{full}'. " + _INGEST_HINT.format(collection=collection)
        )
    return texts


def complete_prompt(config, prompt: str) -> str:
    """Run a one-shot LLM completion and return stripped text."""
    backend = create_backend(config.llm.to_backend_config())
    return backend.complete(prompt).text.strip()
