"""Small CorpusRAG kernel: ingest, ask, summarize, sample, complete.

New utilities should call ``sample`` + ``complete`` rather than constructing
agents, generators, or MCP wrappers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db import DatabaseBackend
from tools.rag.config import RAGConfig


class Corpus:
    """Facade over ingest, retrieval-augmented ask, and study summaries."""

    def __init__(self, config: RAGConfig, db: DatabaseBackend) -> None:
        self.config = config
        self.db = db

    @classmethod
    def from_config_path(cls, path: str | Path = "configs/base.yaml") -> Corpus:
        """Load YAML, build a RAG config and Chroma backend."""
        from cli_common import load_cli_db

        cfg, db = load_cli_db(path, RAGConfig)
        if not cfg.raw:
            from config import BaseConfig, load_config

            base = load_config(Path(path), config_class=BaseConfig)
            cfg.raw = base.raw or base.to_dict()
        return cls(cfg, db)

    def ingest_path(self, path: str | Path, collection: str):
        """Ingest a file or directory into ``rag_<collection>``."""
        from tools.rag.ingest import RAGIngester

        return RAGIngester(self.config, self.db).ingest_path(Path(path), collection)

    def ingest_text(
        self,
        text: str,
        collection: str,
        *,
        doc_id: str | None = None,
        metadata: dict | None = None,
    ):
        """Ingest raw text into ``rag_<collection>``."""
        from tools.rag.agent import RAGAgent

        return RAGAgent(self.config, self.db).ingest_text(
            text, collection, doc_id=doc_id, metadata=metadata
        )

    def ask(self, query: str, collection: str, *, top_k: int | None = None) -> str:
        """Answer ``query`` from ``collection`` (user-facing name, e.g. ``notes``)."""
        from tools.rag.agent import RAGAgent

        return RAGAgent(self.config, self.db).query(query, collection, top_k=top_k)

    def summarize(
        self,
        collection: str,
        *,
        topic: str | None = None,
        length: str = "medium",
    ) -> dict[str, Any]:
        """Summarize ``collection``; returns the generator dict (includes ``summary``)."""
        from tools.summaries import SummaryConfig, SummaryGenerator

        s_cfg = SummaryConfig.from_dict(self.config.raw or self.config.to_dict())
        s_cfg.summary_length = length
        return SummaryGenerator(s_cfg, self.db).generate(collection, topic)

    def sample(self, collection: str, *, query: str, n: int) -> list[str]:
        """Return ``n`` passage texts from ``rag_<collection>`` nearest ``query``."""
        from tools.generation import sample_documents

        return sample_documents(self.db, self.config, collection, query_text=query, n_results=n)

    def complete(self, prompt: str) -> str:
        """One-shot LLM completion using the kernel config."""
        from tools.generation import complete_prompt

        return complete_prompt(self.config, prompt)
