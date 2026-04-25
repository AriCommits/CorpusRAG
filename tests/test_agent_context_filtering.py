"""Tests for agent context filtering."""

import pytest

from src.tools.rag.agent import RAGAgent
from src.tools.rag.config import RAGConfig


@pytest.fixture
def mock_agent(monkeypatch):
    """Create a mock RAG agent for testing context filtering."""
    # Mock the database and config to avoid initialization issues
    monkeypatch.setenv("RAG_CONFIG", "test")

    # Create a minimal agent with mocked dependencies
    class MockDB:
        pass

    class MockConfig:
        class LLM:
            def to_backend_config(self):
                return {}

        llm = LLM()
        paths = None

    agent = RAGAgent.__new__(RAGAgent)
    agent.config = MockConfig()
    agent.db = MockDB()

    return agent


def test_filter_context_includes_all_by_default(mock_agent):
    """Test that filter_context includes all messages by default."""
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "How are you?"},
    ]

    filtered = mock_agent._filter_context(history)
    assert len(filtered) == 3


def test_filter_context_excludes_excluded_messages(mock_agent):
    """Test that filter_context excludes messages with included=False."""
    history = [
        {"role": "user", "content": "Hello", "included": True},
        {"role": "assistant", "content": "Hi", "included": False},
        {"role": "user", "content": "How are you?", "included": True},
    ]

    filtered = mock_agent._filter_context(history)
    assert len(filtered) == 2
    assert filtered[0]["content"] == "Hello"
    assert filtered[1]["content"] == "How are you?"


def test_filter_context_preserves_order(mock_agent):
    """Test that filter_context preserves message order."""
    history = [
        {"role": "user", "content": "1", "included": True},
        {"role": "assistant", "content": "2", "included": False},
        {"role": "user", "content": "3", "included": True},
        {"role": "assistant", "content": "4", "included": False},
        {"role": "user", "content": "5", "included": True},
    ]

    filtered = mock_agent._filter_context(history)
    assert len(filtered) == 3
    assert [msg["content"] for msg in filtered] == ["1", "3", "5"]


def test_filter_context_mixed_format(mock_agent):
    """Test filter_context with mixed included field presence."""
    history = [
        {"role": "user", "content": "First"},  # No included field, should default to True
        {"role": "assistant", "content": "Response", "included": False},
        {"role": "user", "content": "Second", "included": True},
    ]

    filtered = mock_agent._filter_context(history)
    assert len(filtered) == 2
    assert filtered[0]["content"] == "First"
    assert filtered[1]["content"] == "Second"


def test_filter_context_empty_history(mock_agent):
    """Test filter_context with empty history."""
    filtered = mock_agent._filter_context([])
    assert filtered == []


def test_filter_context_all_excluded(mock_agent):
    """Test filter_context when all messages are excluded."""
    history = [
        {"role": "user", "content": "Hello", "included": False},
        {"role": "assistant", "content": "Hi", "included": False},
    ]

    filtered = mock_agent._filter_context(history)
    assert filtered == []
