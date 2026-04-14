"""Data models for database operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Document:
    """Document model for database storage."""

    id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Collection:
    """Collection model for organizing documents."""

    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    document_count: int = 0

    def __post_init__(self) -> None:
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class QueryResult:
    """Query result model."""

    ids: list[str]
    documents: list[str]
    metadatas: list[dict[str, Any]]
    distances: list[float]

    @property
    def count(self) -> int:
        """Get number of results."""
        return len(self.ids)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ids": self.ids,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "distances": self.distances,
            "count": self.count,
        }
