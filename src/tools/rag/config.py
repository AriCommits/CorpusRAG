"""RAG tool configuration."""

from dataclasses import dataclass, field

from corpus_callosum.config.base import BaseConfig


@dataclass
class ChunkingConfig:
    """Text chunking configuration."""

    size: int = 500
    overlap: int = 50


@dataclass
class RetrievalConfig:
    """Retrieval configuration."""

    top_k_semantic: int = 10
    top_k_bm25: int = 10
    top_k_final: int = 5
    rrf_k: int = 60  # Reciprocal Rank Fusion parameter


@dataclass
class RAGConfig(BaseConfig):
    """RAG tool configuration."""

    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
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
        chunking_data = data.get("chunking", {})
        retrieval_data = data.get("retrieval", {})

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            chunking=ChunkingConfig(**chunking_data),
            retrieval=RetrievalConfig(**retrieval_data),
            collection_prefix=data.get("collection_prefix", "rag"),
        )
