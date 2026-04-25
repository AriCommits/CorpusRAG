"""Message and message metadata structures for RAG chat."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MessageMetadata:
    """Metadata for a chat message."""

    message_id: str
    timestamp: datetime
    tokens: int
    role: str  # "user" or "assistant"
    tags: list[str] = field(default_factory=list)
    included: bool = True
