"""Session management for persistent RAG conversations."""

import hashlib
import json
from pathlib import Path


class SessionManager:
    """Manages persistent conversation sessions stored as JSON files with integrity checks."""

    CHECKSUM_LEN = 16  # Use first 16 chars of SHA256 hash

    def __init__(self, sessions_dir: str | Path = ".sessions"):
        """Initialize session manager.

        Args:
            sessions_dir: Directory where session files are stored.
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _compute_checksum(self, data: str) -> str:
        """Compute checksum for data integrity.

        Args:
            data: JSON string to compute checksum for

        Returns:
            First 16 characters of SHA256 hash
        """
        return hashlib.sha256(data.encode()).hexdigest()[: self.CHECKSUM_LEN]

    def _write_with_checksum(self, file_path: Path, data: str) -> None:
        """Write JSON data with checksum header.

        Args:
            file_path: Path to write to
            data: JSON string to write
        """
        checksum = self._compute_checksum(data)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# CHECKSUM:{checksum}\n")
            f.write(data)

    def _read_with_checksum(self, file_path: Path) -> str | None:
        """Read JSON data and verify checksum.

        Args:
            file_path: Path to read from

        Returns:
            JSON string if checksum valid, None if corrupted
        """
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            content = f.read()

        if not first_line.startswith("# CHECKSUM:"):
            # Legacy file without checksum - return content but mark as unverified
            return first_line + content

        stored_checksum = first_line.split(":", 1)[1]
        computed_checksum = self._compute_checksum(content)

        if stored_checksum == computed_checksum:
            return content
        return None  # Corruption detected

    def save_session(self, session_id: str, history: list[dict[str, str]]) -> None:
        """Save conversation history to a session file with checksum.

        Args:
            session_id: Unique identifier for the session.
            history: List of message dictionaries with optional 'included' field.
        """
        file_path = self.sessions_dir / f"{session_id}.json"
        json_data = json.dumps(history, indent=2, ensure_ascii=False)
        self._write_with_checksum(file_path, json_data)

    def load_session(self, session_id: str) -> list[dict[str, str]]:
        """Load conversation history from a session file with checksum verification.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            List of message dictionaries with 'included' field defaulting to True, or empty list if session not found or corrupted.
        """
        file_path = self.sessions_dir / f"{session_id}.json"
        if not file_path.exists():
            return []

        try:
            content = self._read_with_checksum(file_path)
            if content is None:
                # Checksum mismatch - corrupted file
                return []

            history = json.loads(content)
            # Ensure backward compatibility: default 'included' to True
            for msg in history:
                if "included" not in msg:
                    msg["included"] = True
            return history
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
