"""Tests for security validation features."""

import re

import pytest


def _validate_message_id(message_id: str) -> bool:
    """Validate message ID format (UUID only).

    Args:
        message_id: Message identifier to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    return bool(re.match(r"^[a-f0-9\-]{36}$", message_id))


def test_valid_uuid_message_id():
    """Test validation of valid UUID message IDs."""
    valid_uuid = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    assert _validate_message_id(valid_uuid) is True


def test_valid_uuid_lowercase():
    """Test validation of lowercase UUID."""
    valid_uuid = "a1b2c3d4-e5f6-4789-1011-121314151617"
    assert _validate_message_id(valid_uuid) is True


def test_invalid_uuid_wrong_length():
    """Test rejection of UUID with wrong length."""
    assert _validate_message_id("f47ac10b-58cc-4372-a567") is False


def test_invalid_uuid_uppercase():
    """Test rejection of uppercase UUID."""
    invalid_uuid = "F47AC10B-58CC-4372-A567-0E02B2C3D479"
    assert _validate_message_id(invalid_uuid) is False


def test_invalid_uuid_no_dashes():
    """Test rejection of UUID without dashes."""
    invalid_uuid = "f47ac10b58cc4372a5670e02b2c3d479"
    assert _validate_message_id(invalid_uuid) is False


def test_invalid_uuid_wrong_characters():
    """Test rejection of UUID with non-hex characters."""
    invalid_uuid = "g47ac10b-58cc-4372-a567-0e02b2c3d479"
    assert _validate_message_id(invalid_uuid) is False


def test_invalid_empty_string():
    """Test rejection of empty string."""
    assert _validate_message_id("") is False


def test_invalid_regular_string():
    """Test rejection of regular string."""
    assert _validate_message_id("not-a-uuid-at-all") is False
