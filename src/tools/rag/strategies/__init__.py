"""RAG retrieval strategy registry and factory."""

from .base import RAGStrategy, RetrievedDocument
from .hybrid import HybridStrategy
from .keyword import KeywordStrategy
from .semantic import SemanticStrategy

__all__ = [
    "RAGStrategy",
    "RetrievedDocument",
    "HybridStrategy",
    "SemanticStrategy",
    "KeywordStrategy",
    "get_strategy",
    "register_strategy",
    "list_strategies",
]

# Strategy registry
_STRATEGIES: dict[str, type] = {}


def register_strategy(name: str, cls: type) -> None:
    """Register a retrieval strategy.

    Args:
        name: Strategy name
        cls: Strategy class implementing RAGStrategy protocol
    """
    _STRATEGIES[name] = cls


def get_strategy(name: str, **kwargs) -> RAGStrategy:
    """Get a strategy instance by name.

    Args:
        name: Strategy name
        **kwargs: Arguments to pass to strategy constructor

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy is not registered
    """
    if name not in _STRATEGIES:
        raise ValueError(
            f"Unknown strategy: {name}. Available: {', '.join(sorted(_STRATEGIES.keys()))}"
        )
    return _STRATEGIES[name](**kwargs)


def list_strategies() -> list[str]:
    """List all registered strategies.

    Returns:
        List of strategy names
    """
    return sorted(_STRATEGIES.keys())


# Auto-register built-in strategies
register_strategy("hybrid", HybridStrategy)
register_strategy("semantic", SemanticStrategy)
register_strategy("keyword", KeywordStrategy)
