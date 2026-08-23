"""Tests for RAG retrieval strategies."""

import pytest

from tools.rag.config import RAGConfig
from tools.rag.strategies import (
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
            "hybrid",
            vectorstore=vectorstore,
            embedder=embedder,
            parent_store=parent_store,
            config=config,
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
            "semantic",
            vectorstore=vectorstore,
            embedder=embedder,
            parent_store=parent_store,
            config=config,
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
            "keyword",
            vectorstore=vectorstore,
            embedder=embedder,
            parent_store=parent_store,
            config=config,
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

    def test_reranking_can_be_disabled(self):
        """reranking.enabled is honored by StagedStrategy."""
        from unittest.mock import Mock

        config = RAGConfig()
        config.reranking.enabled = False
        doc = RetrievedDocument(id="1", text="t", metadata={}, rank=1, score=1.0)
        strategy = HybridStrategy(
            vectorstore=Mock(),
            embedder=Mock(),
            parent_store=Mock(),
            config=config,
        )
        strategy._vector_search = Mock(return_value=[doc])  # type: ignore[method-assign]
        strategy._keyword_search = Mock(return_value=[doc])  # type: ignore[method-assign]
        strategy._rerank = Mock()  # type: ignore[method-assign]
        out = strategy.retrieve("q", "notes", 3)
        strategy._rerank.assert_not_called()
        assert out[0].id == "1"

    def test_bm25_ignores_other_collections_and_missing_name(self):
        """Parents without this collection_name must not enter BM25."""
        from unittest.mock import Mock

        from langchain_core.documents import Document

        other = Document(page_content="alpha beta", metadata={"collection_name": "other"})
        missing = Document(page_content="alpha beta", metadata={})
        mine = Document(page_content="alpha unique token", metadata={"collection_name": "notes"})
        filler = Document(
            page_content="unrelated words here", metadata={"collection_name": "notes"}
        )
        filler2 = Document(page_content="more filler text", metadata={"collection_name": "notes"})
        parent_store = Mock()
        parent_store.mget_all.return_value = [
            ("a", other),
            ("b", missing),
            ("c", mine),
            ("d", filler),
            ("e", filler2),
        ]
        strategy = KeywordStrategy(
            vectorstore=Mock(),
            embedder=Mock(),
            parent_store=parent_store,
            config=RAGConfig(),
        )
        docs = strategy.retrieve("unique", "notes", top_k=10)
        assert [d.id for d in docs] == ["c"]
