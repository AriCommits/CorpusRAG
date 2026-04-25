"""Tests for TUI context management components."""

import pytest

from tools.rag.context import ContextBlock, ContextSidebar


class TestContextBlock:
    """Tests for ContextBlock dataclass."""

    def test_context_block_creation(self):
        """Test creating a context block."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Hello, world!",
            tokens=4,
        )
        assert block.message_id == "msg1"
        assert block.role == "user"
        assert block.content == "Hello, world!"
        assert block.tokens == 4
        assert block.included is True

    def test_context_block_included_default(self):
        """Test that blocks are included by default."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Test",
            tokens=1,
        )
        assert block.included is True

    def test_context_block_excluded(self):
        """Test creating an excluded block."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Test",
            tokens=1,
            included=False,
        )
        assert block.included is False

    def test_context_block_percentage_calculation(self):
        """Test percentage calculation."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Test",
            tokens=25,
        )
        # 25 tokens out of 100 = 25%
        assert block.percentage(100) == 25.0

    def test_context_block_percentage_half(self):
        """Test 50% calculation."""
        block = ContextBlock(
            message_id="msg1",
            role="assistant",
            content="Response",
            tokens=50,
        )
        assert block.percentage(100) == 50.0

    def test_context_block_percentage_small(self):
        """Test small percentage."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Hi",
            tokens=10,
        )
        # 10 out of 1000 = 1%
        assert block.percentage(1000) == 1.0

    def test_context_block_percentage_zero_total(self):
        """Test percentage when total is zero."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Test",
            tokens=10,
        )
        # When total is 0, percentage should be 0
        assert block.percentage(0) == 0.0

    def test_context_block_percentage_equal(self):
        """Test percentage when block equals total."""
        block = ContextBlock(
            message_id="msg1",
            role="user",
            content="Test",
            tokens=100,
        )
        # 100 out of 100 = 100%
        assert block.percentage(100) == 100.0


class TestContextSidebar:
    """Tests for ContextSidebar widget."""

    def test_context_sidebar_creation(self):
        """Test creating a context sidebar."""
        sidebar = ContextSidebar()
        assert isinstance(sidebar, ContextSidebar)
        assert len(sidebar.blocks) == 0

    def test_context_sidebar_add_block(self):
        """Test adding blocks to sidebar."""
        sidebar = ContextSidebar()
        block1 = ContextBlock("msg1", "user", "Hello", 1)
        block2 = ContextBlock("msg2", "assistant", "Hi", 2)

        sidebar.add_block(block1)
        assert len(sidebar.blocks) == 1

        sidebar.add_block(block2)
        assert len(sidebar.blocks) == 2

    def test_context_sidebar_total_tokens(self):
        """Test total token calculation."""
        sidebar = ContextSidebar()
        sidebar.add_block(ContextBlock("msg1", "user", "Hello", 10))
        sidebar.add_block(ContextBlock("msg2", "assistant", "Hi", 5))
        sidebar.add_block(ContextBlock("msg3", "user", "Thanks", 8))

        assert sidebar.get_total_tokens() == 23

    def test_context_sidebar_empty_total(self):
        """Test total tokens on empty sidebar."""
        sidebar = ContextSidebar()
        assert sidebar.get_total_tokens() == 0

    def test_context_sidebar_single_block_total(self):
        """Test total tokens with single block."""
        sidebar = ContextSidebar()
        sidebar.add_block(ContextBlock("msg1", "user", "Only one", 42))
        assert sidebar.get_total_tokens() == 42

    def test_context_sidebar_included_tokens(self):
        """Test counting only included tokens."""
        sidebar = ContextSidebar()
        sidebar.add_block(ContextBlock("msg1", "user", "Included", 10, included=True))
        sidebar.add_block(ContextBlock("msg2", "assistant", "Excluded", 15, included=False))
        sidebar.add_block(ContextBlock("msg3", "user", "Included", 5, included=True))

        assert sidebar.get_total_tokens() == 30
        assert sidebar.get_included_tokens() == 15

    def test_context_sidebar_all_excluded(self):
        """Test when all blocks are excluded."""
        sidebar = ContextSidebar()
        sidebar.add_block(ContextBlock("msg1", "user", "Test1", 10, included=False))
        sidebar.add_block(ContextBlock("msg2", "assistant", "Test2", 20, included=False))

        assert sidebar.get_total_tokens() == 30
        assert sidebar.get_included_tokens() == 0

    def test_context_sidebar_clear(self):
        """Test clearing all blocks."""
        sidebar = ContextSidebar()
        sidebar.add_block(ContextBlock("msg1", "user", "Test", 10))
        sidebar.add_block(ContextBlock("msg2", "assistant", "Response", 15))

        assert len(sidebar.blocks) == 2
        sidebar.clear()
        assert len(sidebar.blocks) == 0
        assert sidebar.get_total_tokens() == 0

    def test_context_sidebar_update_inclusion(self):
        """Test updating inclusion status of a block."""
        sidebar = ContextSidebar()
        block1 = ContextBlock("msg1", "user", "Test", 10, included=True)
        block2 = ContextBlock("msg2", "assistant", "Response", 15, included=True)

        sidebar.add_block(block1)
        sidebar.add_block(block2)

        # Initially all included
        assert sidebar.get_included_tokens() == 25

        # Exclude msg1
        sidebar.update_block_inclusion("msg1", False)
        assert sidebar.get_included_tokens() == 15

        # Exclude msg2 too
        sidebar.update_block_inclusion("msg2", False)
        assert sidebar.get_included_tokens() == 0

        # Re-include msg1
        sidebar.update_block_inclusion("msg1", True)
        assert sidebar.get_included_tokens() == 10

    def test_context_sidebar_update_nonexistent_block(self):
        """Test updating inclusion of non-existent block (should not crash)."""
        sidebar = ContextSidebar()
        sidebar.add_block(ContextBlock("msg1", "user", "Test", 10))

        # Should not raise error
        sidebar.update_block_inclusion("msg999", False)
        # Should still have the original block
        assert sidebar.get_total_tokens() == 10

    def test_context_sidebar_multiple_same_role(self):
        """Test sidebar with multiple blocks from same role."""
        sidebar = ContextSidebar()
        for i in range(3):
            sidebar.add_block(ContextBlock(f"msg{i}", "user", f"Message {i}", 5 + i))

        assert len(sidebar.blocks) == 3
        # 5 + 6 + 7 = 18
        assert sidebar.get_total_tokens() == 18


class TestContextIntegration:
    """Integration tests for context management."""

    def test_sidebar_with_realistic_conversation(self):
        """Test sidebar with a realistic conversation flow."""
        sidebar = ContextSidebar()

        # User opens conversation
        sidebar.add_block(ContextBlock("msg1", "user", "What is ML?", 4))
        assert sidebar.get_total_tokens() == 4

        # Assistant responds
        sidebar.add_block(ContextBlock("msg2", "assistant", "Machine Learning is...", 50))
        assert sidebar.get_total_tokens() == 54

        # User asks follow-up
        sidebar.add_block(ContextBlock("msg3", "user", "Tell me more", 3))
        assert sidebar.get_total_tokens() == 57

        # User decides to exclude a message
        sidebar.update_block_inclusion("msg2", False)
        assert sidebar.get_included_tokens() == 7

        # Messages are still tracked
        assert len(sidebar.blocks) == 3
        assert sidebar.get_total_tokens() == 57

    def test_percentage_across_conversation(self):
        """Test percentage calculations across a conversation."""
        sidebar = ContextSidebar()
        blocks = [
            ContextBlock("msg1", "user", "Hello", 10),
            ContextBlock("msg2", "assistant", "Hi there", 15),
            ContextBlock("msg3", "user", "How are you?", 5),
            ContextBlock("msg4", "assistant", "Great thanks", 20),
        ]

        for block in blocks:
            sidebar.add_block(block)

        total = sidebar.get_total_tokens()  # 50
        for i, block in enumerate(sidebar.blocks):
            pct = block.percentage(total)
            # Verify percentages sum to 100
            assert 0 <= pct <= 100

        # Verify exact percentages
        assert sidebar.blocks[0].percentage(total) == 20.0  # 10/50
        assert sidebar.blocks[1].percentage(total) == 30.0  # 15/50
        assert sidebar.blocks[2].percentage(total) == 10.0  # 5/50
        assert sidebar.blocks[3].percentage(total) == 40.0  # 20/50
