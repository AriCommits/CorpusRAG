"""Summary tool for CorpusRAG."""


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
    from .config import SummaryConfig
    from .generator import SummaryGenerator

    __all__ = ["SummaryConfig", "SummaryGenerator"]
else:
    # Provide stub that raises helpful error
    class SummaryConfig:  # type: ignore
        """Summary configuration (requires 'generators' extra)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError(
                "Summary generation requires the 'generators' extra.\n"
                "Install with: pip install corpusrag[generators]"
            )

    class SummaryGenerator:  # type: ignore
        """Summary generator (requires 'generators' extra)."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError(
                "Summary generation requires the 'generators' extra.\n"
                "Install with: pip install corpusrag[generators]"
            )

    __all__ = ["SummaryConfig", "SummaryGenerator"]
