"""RAG retrieval logic using parent-child retrieval architecture with pluggable strategies."""

from typing import Any

from db import DatabaseBackend

from .config import RAGConfig
from .pipeline import EmbeddingClient, LocalFileStore
from .strategies import RetrievedDocument, get_strategy, list_strategies
from .vectorstores import ChromaVectorStore


class RAGRetriever:
    """Retrieve relevant documents for RAG using configurable retrieval strategies.

    Supports multiple strategies:
    - hybrid: Vector + BM25 + RRF + reranking (best quality, slowest)
    - semantic: Vector similarity only (balance of speed and quality)
    - keyword: BM25 only (fastest, no embeddings)

    Strategies are pluggable and can be switched at runtime.
    """

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        """Initialize RAG retriever.

        Args:
            config: RAG configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        self.embedder = EmbeddingClient(config)

        # Initialize parent document store
        self.config.parent_store.path.mkdir(parents=True, exist_ok=True)
        self.parent_store = LocalFileStore(str(self.config.parent_store.path))

        # Initialize vectorstore adapter
        self.vectorstore = ChromaVectorStore(db)

        # Initialize strategy
        strategy_name = getattr(config, "strategy", "hybrid")
        self.strategy = get_strategy(
            strategy_name,
            vectorstore=self.vectorstore,
            embedder=self.embedder,
            parent_store=self.parent_store,
            config=config,
        )

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve parent documents using configured strategy.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of parent documents to retrieve
            where: Metadata filter dict

        Returns:
            List of retrieved parent documents
        """
        if top_k is None:
            top_k = self.config.retrieval.top_k_final

        return self.strategy.retrieve(query, collection, top_k, where)

    def set_strategy(self, strategy_name: str) -> None:
        """Switch retrieval strategy at runtime.

        Args:
            strategy_name: Name of strategy to use

        Raises:
            ValueError: If strategy is not registered
        """
        self.strategy = get_strategy(
            strategy_name,
            vectorstore=self.vectorstore,
            embedder=self.embedder,
            parent_store=self.parent_store,
            config=self.config,
        )

    def get_strategy_name(self) -> str:
        """Get current strategy name.

        Returns:
            Current strategy name
        """
        return self.strategy.name

    def get_available_strategies(self) -> list[str]:
        """Get list of available strategies.

        Returns:
            List of strategy names
        """
        return list_strategies()
