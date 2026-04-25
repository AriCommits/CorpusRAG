"""Tests for message metadata structures."""

from datetime import datetime

import pytest

from tools.rag.message import MessageMetadata


class TestMessageMetadata:
    """Tests for message metadata dataclass."""

    def test_create_user_message_metadata(self):
        """Test creating user message metadata."""
        now = datetime.now()
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        assert metadata.message_id == "msg1"
        assert metadata.timestamp == now
        assert metadata.tokens == 10
        assert metadata.role == "user"
        assert metadata.tags == []
        assert metadata.included is True

    def test_create_assistant_message_metadata(self):
        """Test creating assistant message metadata."""
        now = datetime.now()
        metadata = MessageMetadata(
            message_id="msg2",
            timestamp=now,
            tokens=50,
            role="assistant",
        )
        assert metadata.role == "assistant"
        assert metadata.tokens == 50

    def test_message_metadata_with_tags(self):
        """Test message metadata with tags."""
        now = datetime.now()
        tags = ["important", "cs/ml"]
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
            tags=tags,
        )
        assert metadata.tags == ["important", "cs/ml"]
        assert len(metadata.tags) == 2

    def test_message_metadata_excluded(self):
        """Test excluded message metadata."""
        now = datetime.now()
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
            included=False,
        )
        assert metadata.included is False

    def test_message_metadata_default_included(self):
        """Test that messages are included by default."""
        now = datetime.now()
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        assert metadata.included is True

    def test_message_metadata_default_empty_tags(self):
        """Test that default tags is empty list."""
        now = datetime.now()
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        assert metadata.tags == []
        assert isinstance(metadata.tags, list)

    def test_message_metadata_equality(self):
        """Test metadata equality."""
        now = datetime.now()
        m1 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        m2 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        # Dataclass equality checks all fields
        assert m1 == m2

    def test_message_metadata_inequality_different_id(self):
        """Test inequality with different message IDs."""
        now = datetime.now()
        m1 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        m2 = MessageMetadata(
            message_id="msg2",
            timestamp=now,
            tokens=10,
            role="user",
        )
        assert m1 != m2

    def test_message_metadata_inequality_different_tokens(self):
        """Test inequality with different token counts."""
        now = datetime.now()
        m1 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        m2 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=20,
            role="user",
        )
        assert m1 != m2

    def test_message_metadata_inequality_different_role(self):
        """Test inequality with different roles."""
        now = datetime.now()
        m1 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        m2 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="assistant",
        )
        assert m1 != m2

    def test_message_metadata_tags_mutability(self):
        """Test that tags can be modified after creation."""
        now = datetime.now()
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )
        assert metadata.tags == []

        metadata.tags.append("new_tag")
        assert metadata.tags == ["new_tag"]

    def test_message_metadata_with_multiple_tags(self):
        """Test with multiple tags."""
        now = datetime.now()
        tags = ["python", "ml", "transformers", "cs/ml"]
        metadata = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
            tags=tags,
        )
        assert len(metadata.tags) == 4
        assert "python" in metadata.tags
        assert "cs/ml" in metadata.tags

    def test_message_metadata_hashable(self):
        """Test that metadata can be used in sets/dicts (dataclass default)."""
        now = datetime.now()
        m1 = MessageMetadata(
            message_id="msg1",
            timestamp=now,
            tokens=10,
            role="user",
        )

        # Should be usable as dict value (not key unless frozen)
        metadata_dict = {
            "msg1": m1,
        }
        assert metadata_dict["msg1"].message_id == "msg1"


class TestMessageMetadataCollections:
    """Tests for working with collections of metadata."""

    def test_filter_excluded_messages(self):
        """Test filtering out excluded messages."""
        now = datetime.now()
        messages = [
            MessageMetadata("msg1", now, 10, "user", included=True),
            MessageMetadata("msg2", now, 20, "assistant", included=False),
            MessageMetadata("msg3", now, 15, "user", included=True),
            MessageMetadata("msg4", now, 25, "assistant", included=False),
        ]

        included = [m for m in messages if m.included]
        assert len(included) == 2
        assert included[0].message_id == "msg1"
        assert included[1].message_id == "msg3"

    def test_sum_tokens_from_metadata(self):
        """Test summing tokens from metadata."""
        now = datetime.now()
        messages = [
            MessageMetadata("msg1", now, 10, "user"),
            MessageMetadata("msg2", now, 20, "assistant"),
            MessageMetadata("msg3", now, 15, "user"),
        ]

        total_tokens = sum(m.tokens for m in messages)
        assert total_tokens == 45

    def test_sum_tokens_included_only(self):
        """Test summing tokens only from included messages."""
        now = datetime.now()
        messages = [
            MessageMetadata("msg1", now, 10, "user", included=True),
            MessageMetadata("msg2", now, 20, "assistant", included=False),
            MessageMetadata("msg3", now, 15, "user", included=True),
        ]

        included_tokens = sum(m.tokens for m in messages if m.included)
        assert included_tokens == 25

    def test_group_by_role(self):
        """Test grouping metadata by role."""
        now = datetime.now()
        messages = [
            MessageMetadata("msg1", now, 10, "user"),
            MessageMetadata("msg2", now, 20, "assistant"),
            MessageMetadata("msg3", now, 15, "user"),
            MessageMetadata("msg4", now, 25, "assistant"),
        ]

        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]

        assert len(user_messages) == 2
        assert len(assistant_messages) == 2
        assert sum(m.tokens for m in user_messages) == 25
        assert sum(m.tokens for m in assistant_messages) == 45

    def test_find_message_by_id(self):
        """Test finding message by ID."""
        now = datetime.now()
        messages = [
            MessageMetadata("msg1", now, 10, "user"),
            MessageMetadata("msg2", now, 20, "assistant"),
            MessageMetadata("msg3", now, 15, "user"),
        ]

        target = next((m for m in messages if m.message_id == "msg2"), None)
        assert target is not None
        assert target.tokens == 20
        assert target.role == "assistant"

    def test_find_nonexistent_message(self):
        """Test finding non-existent message."""
        now = datetime.now()
        messages = [
            MessageMetadata("msg1", now, 10, "user"),
        ]

        target = next((m for m in messages if m.message_id == "msg999"), None)
        assert target is None
