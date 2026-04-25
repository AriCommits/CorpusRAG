"""Tests for ChatMessage widget with inclusion toggle."""

import pytest


def test_chat_message_can_be_imported():
    """Test that ChatMessage can be imported."""
    try:
        from src.tools.rag.tui import ChatMessage
        assert ChatMessage is not None
    except ImportError:
        pytest.skip("Textual not available")


def test_chat_message_class_exists():
    """Test that ChatMessage class is defined properly."""
    try:
        from src.tools.rag.tui import ChatMessage
        # Verify the class has the expected attributes
        assert hasattr(ChatMessage, "__init__")
        assert hasattr(ChatMessage, "InclusionToggled")
    except ImportError:
        pytest.skip("Textual not available")
