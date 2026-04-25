"""Token estimation utilities for display and verification."""

import math


def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in text using a simple heuristic.

    This uses the common approximation that 1 token ≈ 4 characters.
    For accurate token counting, use the actual tokenizer from your LLM.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Rough approximation: 1 token per 4 characters
    return max(1, len(text) // 4)


def format_tokens(count: int) -> str:
    """Format token count for display.

    Args:
        count: Token count to format

    Returns:
        Formatted string (e.g., "500", "1.5k", "10.0k")
    """
    if count < 1000:
        return str(count)

    # Format as k (thousands)
    thousands = count / 1000.0
    return f"{thousands:.1f}k"
