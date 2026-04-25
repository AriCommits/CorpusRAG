"""Flashcard tool for CorpusRAG."""


def _check_available() -> bool:
    """Check if generators extra is installed.

    Returns:
        True if tiktoken (generators extra) is available, False otherwise
    """
    try:
        import tiktoken  # noqa: F401
        return True
    except ImportError:
        return False


GENERATORS_AVAILABLE = _check_available()

if GENERATORS_AVAILABLE:
    from .config import FlashcardConfig
    from .generator import FlashcardGenerator

    __all__ = ["FlashcardConfig", "FlashcardGenerator"]
else:
    # Provide stub that raises helpful error
    class FlashcardConfig:  # type: ignore
        """Flashcard configuration (requires 'generators' extra)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError(
                "Flashcard generation requires the 'generators' extra.\n"
                "Install with: pip install corpusrag[generators]"
            )

    class FlashcardGenerator:  # type: ignore
        """Flashcard generator (requires 'generators' extra)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError(
                "Flashcard generation requires the 'generators' extra.\n"
                "Install with: pip install corpusrag[generators]"
            )

    __all__ = ["FlashcardConfig", "FlashcardGenerator"]
