"""RAG tool configuration."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from config.base import BaseConfig


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""

    # Parent chunks come from MarkdownHeaderTextSplitter (full sections)
    child_chunk_size: int = 800
    child_chunk_overlap: int = 100
    adaptive: bool = True


class RetrievalConfig(BaseModel):
    """Retrieval configuration."""

    top_k_semantic: int = 50
    top_k_bm25: int = 25
    top_k_final: int = 10
    rrf_k: int = 80  # Reciprocal Rank Fusion parameter


class RerankingConfig(BaseModel):
    """Reranking configuration."""

    enabled: bool = True
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class ParentStoreConfig(BaseModel):
    """Parent document store configuration."""

    path: Path = Field(default_factory=lambda: Path("./parent_store"))


class RAGConfig(BaseConfig):
    """RAG tool configuration."""

    strategy: str = "hybrid"  # hybrid | semantic | keyword
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    reranking: RerankingConfig = Field(default_factory=RerankingConfig)
    parent_store: ParentStoreConfig = Field(default_factory=ParentStoreConfig)
    collection_prefix: str = "rag"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RAGConfig":
        """Create ragconfig from dictionary."""
        base_config, tool_data = BaseConfig.split_section(data, "rag")
        merged = base_config.model_dump(mode="json", exclude={"raw"})

        # Merge dictionary data correctly for nested dicts (like chunking, retrieval)
        for k, v in tool_data.items():
            if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                merged[k].update(v)
            else:
                merged[k] = v

        inst = cls.model_validate(merged)
        inst.raw = data
        return inst
