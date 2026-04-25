"""Tests for session checksum integrity verification."""

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


def test_checksum_computation(temp_session_dir):
    """Test that checksums are computed consistently."""
    manager = SessionManager(temp_session_dir)
    data = json.dumps([{"role": "user", "content": "hello"}])
    checksum1 = manager._compute_checksum(data)
    checksum2 = manager._compute_checksum(data)
    assert checksum1 == checksum2
    assert len(checksum1) == 16  # First 16 chars of SHA256


def test_save_with_checksum(temp_session_dir):
    """Test that sessions are saved with checksum."""
    manager = SessionManager(temp_session_dir)
    history = [{"role": "user", "content": "test"}]
    manager.save_session("test", history)

    session_file = Path(temp_session_dir) / "test.json"
    with open(session_file) as f:
        first_line = f.readline()

    assert first_line.startswith("# CHECKSUM:")


def test_load_with_valid_checksum(temp_session_dir):
    """Test loading session with valid checksum."""
    manager = SessionManager(temp_session_dir)
    history = [{"role": "user", "content": "hello"}]
    manager.save_session("test", history)

    loaded = manager.load_session("test")
    assert len(loaded) == 1
    assert loaded[0]["content"] == "hello"


def test_load_with_corrupted_checksum(temp_session_dir):
    """Test that corrupted sessions are detected and rejected."""
    manager = SessionManager(temp_session_dir)
    history = [{"role": "user", "content": "hello"}]
    manager.save_session("test", history)

    # Corrupt the session file
    session_file = Path(temp_session_dir) / "test.json"
    content = session_file.read_text()
    corrupted = content.replace("hello", "modified")
    session_file.write_text(corrupted)

    # Should return empty list due to checksum mismatch
    loaded = manager.load_session("test")
    assert loaded == []


def test_backward_compat_legacy_session(temp_session_dir):
    """Test loading legacy sessions without checksum."""
    manager = SessionManager(temp_session_dir)

    # Create legacy session file without checksum
    session_file = Path(temp_session_dir) / "legacy.json"
    history = [{"role": "user", "content": "legacy"}]
    with open(session_file, "w") as f:
        json.dump(history, f)

    # Should still load legacy sessions
    loaded = manager.load_session("legacy")
    assert len(loaded) == 1
    assert loaded[0]["content"] == "legacy"


def test_checksum_different_content(temp_session_dir):
    """Test that different content produces different checksums."""
    manager = SessionManager(temp_session_dir)
    checksum1 = manager._compute_checksum('{"data": "one"}')
    checksum2 = manager._compute_checksum('{"data": "two"}')
    assert checksum1 != checksum2


def test_save_load_roundtrip_with_included(temp_session_dir):
    """Test complete roundtrip with included field and checksum."""
    manager = SessionManager(temp_session_dir)
    original = [
        {"role": "user", "content": "Q1", "included": True},
        {"role": "assistant", "content": "A1", "included": False},
    ]
    manager.save_session("test", original)

    loaded = manager.load_session("test")
    assert loaded == original
