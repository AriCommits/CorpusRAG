"""Conversation memory for multi-turn interactions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

logger = __import__("logging").getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Conversation:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    max_turns: int = 10

    def add_message(self, role: str, content: str) -> None:
        if len(self.messages) >= self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2 - 2) :]
        self.messages.append(Message(role=role, content=content))

    def to_chat_messages(self) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


class ConversationStore:
    """In-memory store for conversation sessions."""

    def __init__(self, max_sessions: int = 1000, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, Conversation] = {}
        self._last_access: dict[str, float] = {}
        self._max_sessions = max_sessions
        self._ttl_seconds = ttl_seconds

    def get_or_create(self, session_id: str, max_turns: int = 10) -> Conversation:
        self._cleanup_expired()
        if session_id not in self._sessions:
            if len(self._sessions) >= self._max_sessions:
                oldest = min(self._last_access, key=lambda k: self._last_access[k])
                del self._sessions[oldest]
                del self._last_access[oldest]
            self._sessions[session_id] = Conversation(
                session_id=session_id,
                max_turns=max_turns,
            )
        self._last_access[session_id] = time.time()
        return self._sessions[session_id]

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [sid for sid, ts in self._last_access.items() if now - ts > self._ttl_seconds]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._last_access.pop(sid, None)


_store = ConversationStore()


def get_conversation(session_id: str, max_turns: int = 10) -> Conversation:
    return _store.get_or_create(session_id, max_turns=max_turns)
