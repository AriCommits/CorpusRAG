"""RAG tool configuration."""

from dataclasses import dataclass, field
from pathlib import Path

from config.base import BaseConfig


@dataclass
class ChunkingConfig:
    """Text chunking configuration."""

    # Parent chunks come from MarkdownHeaderTextSplitter (full sections)
    child_chunk_size: int = 800
    child_chunk_overlap: int = 100


@dataclass
class RetrievalConfig:
    """Retrieval configuration."""

    top_k_semantic: int = 50
    top_k_bm25: int = 25
    top_k_final: int = 10
    rrf_k: int = 80  # Reciprocal Rank Fusion parameter


@dataclass
class ParentStoreConfig:
    """Parent document store configuration."""

    type: str = "local_file"  # local_file | in_memory
    path: Path = field(default_factory=lambda: Path("./parent_store"))


@dataclass
class RAGConfig(BaseConfig):
    """RAG tool configuration."""

    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    parent_store: ParentStoreConfig = field(default_factory=ParentStoreConfig)
    collection_prefix: str = "rag"

    @classmethod
    def from_dict(cls, data: dict) -> "RAGConfig":
        """Create RAG config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            RAGConfig instance
        """
        # Get base config
        base_config = super().from_dict(data)

        # Get RAG-specific config
        rag_data = data.get("rag", {})
        chunking_data = rag_data.get("chunking", {})
        retrieval_data = rag_data.get("retrieval", {})
        parent_store_data = rag_data.get("parent_store", {})
        collection_prefix = rag_data.get("collection_prefix")

        # Handle parent_store path conversion
        if "path" in parent_store_data and isinstance(parent_store_data["path"], str):
            parent_store_data["path"] = Path(parent_store_data["path"])

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            chunking=(ChunkingConfig(**chunking_data) if chunking_data else ChunkingConfig()),
            retrieval=(RetrievalConfig(**retrieval_data) if retrieval_data else RetrievalConfig()),
            parent_store=(
                ParentStoreConfig(**parent_store_data) if parent_store_data else ParentStoreConfig()
            ),
            collection_prefix=collection_prefix or "rag",
        )
