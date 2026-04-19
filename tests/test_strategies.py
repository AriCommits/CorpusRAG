"""Tests for RAG retrieval strategies."""

import pytest

from src.tools.rag.config import RAGConfig
from src.tools.rag.strategies import (
    HybridStrategy,
    KeywordStrategy,
    RetrievedDocument,
    SemanticStrategy,
    get_strategy,
    list_strategies,
    register_strategy,
)


class TestStrategyRegistry:
    """Tests for strategy registry."""

    def test_built_in_strategies_registered(self):
        """Built-in strategies are registered on import."""
        strategies = list_strategies()
        assert "hybrid" in strategies
        assert "semantic" in strategies
        assert "keyword" in strategies

    def test_get_strategy_hybrid(self):
        """get_strategy returns HybridStrategy for 'hybrid'."""
        # Mock dependencies
        from unittest.mock import Mock

        vectorstore = Mock()
        embedder = Mock()
        parent_store = Mock()
        config = RAGConfig()

        strategy = get_strategy(
            "hybrid", vectorstore=vectorstore, embedder=embedder, parent_store=parent_store, config=config
        )
        assert strategy.name == "hybrid"
        assert isinstance(strategy, HybridStrategy)

    def test_get_strategy_semantic(self):
        """get_strategy returns SemanticStrategy for 'semantic'."""
        from unittest.mock import Mock

        vectorstore = Mock()
        embedder = Mock()
        parent_store = Mock()
        config = RAGConfig()

        strategy = get_strategy(
            "semantic", vectorstore=vectorstore, embedder=embedder, parent_store=parent_store, config=config
        )
        assert strategy.name == "semantic"
        assert isinstance(strategy, SemanticStrategy)

    def test_get_strategy_keyword(self):
        """get_strategy returns KeywordStrategy for 'keyword'."""
        from unittest.mock import Mock

        vectorstore = Mock()
        embedder = Mock()
        parent_store = Mock()
        config = RAGConfig()

        strategy = get_strategy(
            "keyword", vectorstore=vectorstore, embedder=embedder, parent_store=parent_store, config=config
        )
        assert strategy.name == "keyword"
        assert isinstance(strategy, KeywordStrategy)

    def test_get_unknown_strategy_raises(self):
        """get_strategy raises ValueError for unknown strategy."""
        from unittest.mock import Mock

        vectorstore = Mock()
        embedder = Mock()
        parent_store = Mock()
        config = RAGConfig()

        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy(
                "unknown",
                vectorstore=vectorstore,
                embedder=embedder,
                parent_store=parent_store,
                config=config,
            )

    def test_register_custom_strategy(self):
        """Custom strategies can be registered."""

        class CustomStrategy:
            name = "custom"

        register_strategy("custom", CustomStrategy)
        strategies = list_strategies()
        assert "custom" in strategies

    def test_list_strategies_returns_sorted_list(self):
        """list_strategies returns sorted list of names."""
        strategies = list_strategies()
        assert strategies == sorted(strategies)


class TestRetrievedDocument:
    """Tests for RetrievedDocument dataclass."""

    def test_retrieved_document_creation(self):
        """RetrievedDocument instances are created correctly."""
        doc = RetrievedDocument(
            id="doc1", text="content", metadata={"key": "value"}, rank=1, score=0.95
        )

        assert doc.id == "doc1"
        assert doc.text == "content"
        assert doc.metadata == {"key": "value"}
        assert doc.rank == 1
        assert doc.score == 0.95

    def test_retrieved_document_default_score(self):
        """RetrievedDocument has default score of 0.0."""
        doc = RetrievedDocument(id="doc1", text="content", metadata={}, rank=1)
        assert doc.score == 0.0

    def test_retrieved_document_frozen(self):
        """RetrievedDocument is frozen (immutable)."""
        doc = RetrievedDocument(id="doc1", text="content", metadata={}, rank=1)
        with pytest.raises(AttributeError):
            doc.id = "doc2"


class TestStrategyConfiguration:
    """Tests for strategy configuration."""

    def test_config_strategy_defaults_to_hybrid(self):
        """RAGConfig strategy field defaults to 'hybrid'."""
        config = RAGConfig()
        assert config.strategy == "hybrid"

    def test_reranking_config_defaults(self):
        """RerankingConfig has correct defaults."""
        config = RAGConfig()
        assert config.reranking.enabled is True
        assert "cross-encoder" in config.reranking.model

    def test_vectorstore_config_defaults(self):
        """VectorStoreConfig has correct defaults."""
        config = RAGConfig()
        assert config.vectorstore.backend == "chromadb"
        assert config.vectorstore.langchain_class is None
