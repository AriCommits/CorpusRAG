"""Input validation for prompt injection and malicious input prevention (CWE-94)."""

import logging
import re
from typing import List, Optional

from .security import SecurityError

logger = logging.getLogger(__name__)

# Constants for validation
MAX_QUERY_LENGTH = 5000
MAX_COLLECTION_NAME_LENGTH = 256
MAX_SPECIAL_CHAR_PERCENTAGE = 30
MAX_CONVERSATION_HISTORY = 50
MAX_CHUNK_SIZE = 2000
MIN_QUERY_LENGTH = 1

# Prompt injection attack patterns
PROMPT_INJECTION_PATTERNS: List[re.Pattern] = [
    # Instruction override attempts
    re.compile(r"ignore\s+.*?previous.*?instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+.*?(admin|system|root)", re.IGNORECASE),
    re.compile(r"forget\s+.*?previous", re.IGNORECASE),
    
    # System markers
    re.compile(r"\[SYSTEM\s*:", re.IGNORECASE),
    re.compile(r"\[ADMIN\s*:", re.IGNORECASE),
    re.compile(r"\[SECURITY\s*:", re.IGNORECASE),
    re.compile(r"\{SYSTEM\s*:", re.IGNORECASE),
    
    # Special tokens and prompt breaks
    re.compile(r"<\|[\w\s]+\|>"),
    re.compile(r"###\s*(SYSTEM|ADMIN|INSTRUCTION)", re.IGNORECASE),
    
    # Code execution patterns
    re.compile(r"\bimport\s+", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    re.compile(r"\bexecfile\s*\(", re.IGNORECASE),
    re.compile(r"\bos\.system", re.IGNORECASE),
    re.compile(r"\bsubprocess\.", re.IGNORECASE),
    
    # Template injection patterns
    re.compile(r"\{\{.*?__.*?\}\}", re.IGNORECASE),  # Jinja2-like
    re.compile(r"\{%.*?%(})?", re.IGNORECASE),  # Template syntax
]


class InputValidator:
    """Validates user inputs for prompt injection and other malicious patterns."""

    def __init__(
        self,
        max_query_length: int = MAX_QUERY_LENGTH,
        max_collection_name_length: int = MAX_COLLECTION_NAME_LENGTH,
    ):
        """Initialize validator with configurable limits.

        Args:
            max_query_length: Maximum allowed query length
            max_collection_name_length: Maximum collection name length
        """
        self.max_query_length = max_query_length
        self.max_collection_name_length = max_collection_name_length

    def validate_query(self, query: Optional[str]) -> str:
        """Validate user query for injection attacks.

        Args:
            query: User query string

        Returns:
            Sanitized query

        Raises:
            SecurityError: If query fails validation
        """
        # Check for None or empty
        if not query or not isinstance(query, str):
            raise SecurityError("Query must be a non-empty string")

        # Check length
        if len(query) < MIN_QUERY_LENGTH:
            raise SecurityError("Query is empty")

        if len(query) > self.max_query_length:
            raise SecurityError(
                f"Query too long: {len(query)} characters (max: {self.max_query_length})"
            )

        # Remove control characters
        sanitized = "".join(c for c in query if ord(c) >= 32 or c in "\t\n\r")

        # Normalize whitespace
        sanitized = " ".join(sanitized.split())

        # Scan for injection patterns
        self._scan_for_injection_patterns(sanitized)

        # Check for excessive special characters
        self._check_special_character_ratio(sanitized)

        logger.debug(f"Query validated successfully: {len(sanitized)} chars")

        return sanitized

    def validate_collection_name(self, name: Optional[str]) -> str:
        """Validate collection name.

        Args:
            name: Collection name

        Returns:
            Validated collection name

        Raises:
            SecurityError: If validation fails
        """
        if not name or not isinstance(name, str):
            raise SecurityError("Collection name must be a non-empty string")

        if len(name) > self.max_collection_name_length:
            raise SecurityError(
                f"Collection name too long: {len(name)} characters "
                f"(max: {self.max_collection_name_length})"
            )

        # Only allow alphanumeric, underscores, and hyphens
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            raise SecurityError(
                "Collection name can only contain alphanumeric characters, "
                "underscores, and hyphens"
            )

        logger.debug(f"Collection name validated: {name}")

        return name

    def validate_top_k(self, top_k: Optional[int], min_val: int = 1, max_val: int = 100) -> int:
        """Validate top_k parameter for retrieval.

        Args:
            top_k: Number of top results
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Validated top_k

        Raises:
            SecurityError: If validation fails
        """
        if not isinstance(top_k, int):
            raise SecurityError("top_k must be an integer")

        if not min_val <= top_k <= max_val:
            raise SecurityError(
                f"top_k must be between {min_val} and {max_val}, got {top_k}"
            )

        return top_k

    def validate_conversation_history(
        self, history: Optional[list], max_messages: int = MAX_CONVERSATION_HISTORY
    ) -> list:
        """Validate conversation history.

        Args:
            history: List of conversation messages
            max_messages: Maximum allowed messages

        Returns:
            Validated history

        Raises:
            SecurityError: If validation fails
        """
        if not isinstance(history, list):
            raise SecurityError("Conversation history must be a list")

        if len(history) > max_messages:
            raise SecurityError(
                f"Conversation history too long: {len(history)} messages "
                f"(max: {max_messages})"
            )

        # Validate each message
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                raise SecurityError(f"Message {i} must be a dictionary")

            if "role" not in msg or "content" not in msg:
                raise SecurityError(
                    f"Message {i} must have 'role' and 'content' fields"
                )

            # Only allow user and assistant roles
            if msg["role"] not in ("user", "assistant"):
                raise SecurityError(
                    f"Message {i} has invalid role: {msg['role']}. "
                    f"Only 'user' and 'assistant' allowed"
                )

            # Validate content
            if not isinstance(msg["content"], str):
                raise SecurityError(f"Message {i} content must be a string")

        logger.debug(f"Conversation history validated: {len(history)} messages")

        return history

    def validate_chunk_text(self, text: Optional[str], max_size: int = MAX_CHUNK_SIZE) -> str:
        """Validate chunk text size.

        Args:
            text: Text chunk
            max_size: Maximum allowed size

        Returns:
            Validated text

        Raises:
            SecurityError: If validation fails
        """
        if not isinstance(text, str):
            raise SecurityError("Chunk text must be a string")

        if len(text) > max_size:
            raise SecurityError(
                f"Chunk text too large: {len(text)} characters (max: {max_size})"
            )

        return text

    def _scan_for_injection_patterns(self, text: str) -> None:
        """Scan text for known injection patterns.

        Args:
            text: Text to scan

        Raises:
            SecurityError: If suspicious patterns detected
        """
        for i, pattern in enumerate(PROMPT_INJECTION_PATTERNS):
            if pattern.search(text):
                raise SecurityError(
                    f"Suspicious patterns detected in input (pattern: {i}). "
                    f"This query may be attempting prompt injection"
                )

    def _check_special_character_ratio(self, text: str) -> None:
        """Check if text has too many special characters.

        Args:
            text: Text to check

        Raises:
            SecurityError: If too many special characters
        """
        # Count non-alphanumeric, non-space characters
        special_count = sum(1 for c in text if not c.isalnum() and c != " ")
        total = len(text)

        if total > 0:
            ratio = (special_count / total) * 100
            if ratio > MAX_SPECIAL_CHAR_PERCENTAGE:
                raise SecurityError(
                    f"Input has excessive special characters: {ratio:.1f}% "
                    f"(max: {MAX_SPECIAL_CHAR_PERCENTAGE}%)"
                )


# Singleton instance for reuse
_validator_instance: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get or create singleton validator instance.

    Returns:
        InputValidator instance
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = InputValidator()
    return _validator_instance
