"""Data models for database operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """Document model for database storage."""

    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Collection:
    """Collection model for organizing documents."""

    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    document_count: int = 0

    def __post_init__(self) -> None:
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class QueryResult:
    """Query result model."""

    ids: List[str]
    documents: List[str]
    metadatas: List[Dict[str, Any]]
    distances: List[float]

    @property
    def count(self) -> int:
        """Get number of results."""
        return len(self.ids)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ids": self.ids,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "distances": self.distances,
            "count": self.count,
        }
