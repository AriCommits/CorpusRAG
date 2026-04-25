"""Quiz generation tool."""


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
    from .config import QuizConfig
    from .generator import QuizGenerator

    __all__ = ["QuizConfig", "QuizGenerator"]
else:
    # Provide stub that raises helpful error
    class QuizConfig:  # type: ignore
        """Quiz configuration (requires 'generators' extra)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError(
                "Quiz generation requires the 'generators' extra.\n"
                "Install with: pip install corpusrag[generators]"
            )

    class QuizGenerator:  # type: ignore
        """Quiz generator (requires 'generators' extra)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError(
                "Quiz generation requires the 'generators' extra.\n"
                "Install with: pip install corpusrag[generators]"
            )

    __all__ = ["QuizConfig", "QuizGenerator"]
