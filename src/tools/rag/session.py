"""Session management for persistent RAG conversations."""

import json
from pathlib import Path


class SessionManager:
    """Manages persistent conversation sessions stored as JSON files."""

    def __init__(self, sessions_dir: str | Path = ".sessions"):
        """Initialize session manager.

        Args:
            sessions_dir: Directory where session files are stored.
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_id: str, history: list[dict[str, str]]) -> None:
        """Save conversation history to a session file.

        Args:
            session_id: Unique identifier for the session.
            history: List of message dictionaries.
        """
        file_path = self.sessions_dir / f"{session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def load_session(self, session_id: str) -> list[dict[str, str]]:
        """Load conversation history from a session file.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            List of message dictionaries, or empty list if session not found.
        """
        file_path = self.sessions_dir / f"{session_id}.json"
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def list_sessions(self) -> list[str]:
        """List all available session IDs.

        Returns:
            List of session IDs (filenames without .json).
        """
        return [f.stem for f in self.sessions_dir.glob("*.json")]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            True if deleted, False if not found.
        """
        file_path = self.sessions_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
