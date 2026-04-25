"""Tests for session inclusion/exclusion functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from src.tools.rag.session import SessionManager


@pytest.fixture
def temp_session_dir():
    """Create a temporary directory for sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_save_session_with_included_field(temp_session_dir):
    """Test saving messages with included field."""
    manager = SessionManager(temp_session_dir)
    history = [
        {"role": "user", "content": "Hello", "included": True},
        {"role": "assistant", "content": "Hi there", "included": True},
        {"role": "user", "content": "How are you?", "included": False},
    ]

    manager.save_session("test_session", history)

    # Verify file exists and contains the included field
    session_file = Path(temp_session_dir) / "test_session.json"
    assert session_file.exists()

    with open(session_file) as f:
        saved_data = json.load(f)

    assert len(saved_data) == 3
    assert saved_data[0]["included"] is True
    assert saved_data[2]["included"] is False


def test_load_session_defaults_included_to_true(temp_session_dir):
    """Test that loading sessions defaults included to True for backward compatibility."""
    session_file = Path(temp_session_dir) / "test_session.json"

    # Create a session file without included field (simulating old format)
    old_format_data = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]

    with open(session_file, "w") as f:
        json.dump(old_format_data, f)

    manager = SessionManager(temp_session_dir)
    loaded_history = manager.load_session("test_session")

    # All messages should default to included=True
    assert len(loaded_history) == 2
    assert all(msg.get("included") is True for msg in loaded_history)


def test_load_session_preserves_included_field(temp_session_dir):
    """Test that loading sessions preserves the included field."""
    manager = SessionManager(temp_session_dir)
    original_history = [
        {"role": "user", "content": "Hello", "included": True},
        {"role": "assistant", "content": "Hi", "included": False},
    ]

    manager.save_session("test_session", original_history)
    loaded_history = manager.load_session("test_session")

    assert loaded_history[0]["included"] is True
    assert loaded_history[1]["included"] is False


def test_load_nonexistent_session(temp_session_dir):
    """Test loading a non-existent session returns empty list."""
    manager = SessionManager(temp_session_dir)
    history = manager.load_session("nonexistent")
    assert history == []


def test_mixed_included_format(temp_session_dir):
    """Test loading messages with mixed included field presence."""
    manager = SessionManager(temp_session_dir)
    history = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Response", "included": False},
        {"role": "user", "content": "Second", "included": True},
    ]

    manager.save_session("test_session", history)
    loaded = manager.load_session("test_session")

    # First message should default to True
    assert loaded[0]["included"] is True
    # Second message should preserve False
    assert loaded[1]["included"] is False
    # Third message should preserve True
    assert loaded[2]["included"] is True
