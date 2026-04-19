"""Base abstraction for RAG retrieval strategies."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RetrievedDocument:
    """A retrieved parent document."""

    id: str
    text: str
    metadata: dict[str, Any]
    rank: int
    score: float = 0.0


class RAGStrategy(Protocol):
    """Protocol for pluggable RAG retrieval strategies.

    Any class implementing this protocol can be used as a retrieval strategy.
    """

    name: str

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve relevant documents using this strategy.

        Args:
            query: Search query string
            collection: Collection name
            top_k: Number of documents to retrieve
            where: Optional metadata filter dict

        Returns:
            List of retrieved documents ranked by relevance
        """
        ...

    def initialize(self, collection: str) -> None:
        """Initialize any indexes or caches for a collection.

        Args:
            collection: Collection name to initialize
        """
        ...
