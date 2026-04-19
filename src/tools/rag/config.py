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
class RerankingConfig:
    """Reranking configuration."""

    enabled: bool = True
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class VectorStoreConfig:
    """VectorStore backend configuration."""

    backend: str = "chromadb"  # chromadb | langchain
    langchain_class: str | None = None  # e.g., "langchain_qdrant.QdrantVectorStore"
    langchain_kwargs: dict = field(default_factory=dict)


@dataclass
class ParentStoreConfig:
    """Parent document store configuration."""

    type: str = "local_file"  # local_file | in_memory
    path: Path = field(default_factory=lambda: Path("./parent_store"))


@dataclass
class RAGConfig(BaseConfig):
    """RAG tool configuration."""

    strategy: str = "hybrid"  # hybrid | semantic | keyword
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    reranking: RerankingConfig = field(default_factory=RerankingConfig)
    parent_store: ParentStoreConfig = field(default_factory=ParentStoreConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
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
        strategy = rag_data.get("strategy", "hybrid")
        chunking_data = rag_data.get("chunking", {})
        retrieval_data = rag_data.get("retrieval", {})
        reranking_data = rag_data.get("reranking", {})
        parent_store_data = rag_data.get("parent_store", {})
        vectorstore_data = rag_data.get("vectorstore", {})
        collection_prefix = rag_data.get("collection_prefix", "rag")

        # Handle parent_store path conversion
        if "path" in parent_store_data and isinstance(parent_store_data["path"], str):
            parent_store_data["path"] = Path(parent_store_data["path"])

        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            strategy=strategy,
            chunking=(ChunkingConfig(**chunking_data) if chunking_data else ChunkingConfig()),
            retrieval=(RetrievalConfig(**retrieval_data) if retrieval_data else RetrievalConfig()),
            reranking=(RerankingConfig(**reranking_data) if reranking_data else RerankingConfig()),
            parent_store=(
                ParentStoreConfig(**parent_store_data) if parent_store_data else ParentStoreConfig()
            ),
            vectorstore=(
                VectorStoreConfig(**vectorstore_data) if vectorstore_data else VectorStoreConfig()
            ),
            collection_prefix=collection_prefix,
        )
