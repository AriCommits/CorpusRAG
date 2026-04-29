"""Token estimation utilities for display and verification."""

from functools import lru_cache


@lru_cache(maxsize=1)
def _get_tokenizer():
    """Get cached tiktoken encoder, or None if unavailable."""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except (ImportError, Exception):
        return None


def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in text.

    Uses tiktoken (cl100k_base) when available (install with: pip install corpusrag[generators]).
    Falls back to len(text) // 4 heuristic otherwise.

    Args:
        text: Text to estimate tokens for

    Returns:
        Token count (exact with tiktoken, approximate without)
    """
    if not text:
        return 0
    enc = _get_tokenizer()
    if enc is not None:
        return len(enc.encode(text))
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
    thousands = count / 1000.0
    return f"{thousands:.1f}k"
