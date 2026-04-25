"""Context management and context sidebar for TUI."""

from dataclasses import dataclass


@dataclass
class ContextBlock:
    """Represents a block of context (message) with metadata."""

    message_id: str
    role: str  # "user" or "assistant"
    content: str
    tokens: int
    included: bool = True

    def percentage(self, total_tokens: int) -> float:
        """Calculate percentage of total tokens this message represents.

        Args:
            total_tokens: Total tokens in context

        Returns:
            Percentage (0-100)
        """
        if total_tokens == 0:
            return 0.0
        return (self.tokens / total_tokens) * 100


class ContextSidebar:
    """Manager for context blocks and token usage tracking."""

    def __init__(self):
        self.blocks: list[ContextBlock] = []

    def add_block(self, block: ContextBlock) -> None:
        """Add a context block to the sidebar.

        Args:
            block: ContextBlock to add
        """
        self.blocks.append(block)

    def get_total_tokens(self) -> int:
        """Get total tokens across all blocks.

        Returns:
            Sum of tokens in all blocks
        """
        return sum(block.tokens for block in self.blocks)

    def get_included_tokens(self) -> int:
        """Get total tokens from included (not excluded) blocks.

        Returns:
            Sum of tokens in included blocks only
        """
        return sum(block.tokens for block in self.blocks if block.included)

    def clear(self) -> None:
        """Clear all context blocks."""
        self.blocks = []

    def update_block_inclusion(self, message_id: str, included: bool) -> None:
        """Update inclusion status of a block.

        Args:
            message_id: ID of message/block to update
            included: Whether block should be included in context
        """
        for block in self.blocks:
            if block.message_id == message_id:
                block.included = included
                break
