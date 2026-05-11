"""Rate limiting for resource-intensive operations (CWE-770)."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    ingestion_per_hour: int = 10
    max_file_size_mb: int = 100
    max_concurrent_ingestions: int = 2
    embedding_calls_per_minute: int = 100
    pdf_pages_per_hour: int = 1000
    query_calls_per_minute: int = 60


class OperationRateLimiter:
    """Rate limiter for tracking and limiting resource-intensive operations."""

    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter.

        Args:
            config: RateLimitConfig instance
        """
        self.config = config
        self._lock = Lock()

        # Track operation history: (user, operation_type) -> [timestamps]
        self._operation_history: dict[tuple[str, str], list] = defaultdict(list)

        # Track active operations: (user, operation_type) -> count
        self._active_operations: dict[tuple[str, str], int] = defaultdict(int)

    def check_operation_limit(
        self,
        user_id: str,
        operation_type: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """Check if operation is allowed based on limit.

        Uses sliding window approach to count operations in the specified window.

        Args:
            user_id: User identifier
            operation_type: Type of operation (e.g., 'ingestion', 'embedding')
            limit: Maximum operations allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if operation is allowed, False if rate limited
        """
        with self._lock:
            key = (user_id, operation_type)
            now = time.time()

            # Remove old entries outside the window
            cutoff_time = now - window_seconds
            self._operation_history[key] = [
                ts for ts in self._operation_history[key] if ts > cutoff_time
            ]

            # Check if limit exceeded
            if len(self._operation_history[key]) >= limit:
                logger.warning(
                    f"Rate limit exceeded for {user_id}/{operation_type}: "
                    f"{len(self._operation_history[key])} operations in {window_seconds}s"
                )
                return False

            # Record this operation
            self._operation_history[key].append(now)
            return True

    def check_concurrent_limit(
        self, user_id: str, operation_type: str, max_concurrent: int
    ) -> bool:
        """Check if concurrent operation limit is not exceeded.

        Args:
            user_id: User identifier
            operation_type: Type of operation
            max_concurrent: Maximum concurrent operations allowed

        Returns:
            True if concurrent limit allows, False if exceeded
        """
        with self._lock:
            key = (user_id, operation_type)
            if self._active_operations[key] >= max_concurrent:
                logger.warning(
                    f"Concurrent limit exceeded for {user_id}/{operation_type}: "
                    f"{self._active_operations[key]} operations (max: {max_concurrent})"
                )
                return False
            return True

    def start_operation(self, user_id: str, operation_type: str) -> None:
        """Mark start of an operation (increments counter).

        Args:
            user_id: User identifier
            operation_type: Type of operation
        """
        with self._lock:
            key = (user_id, operation_type)
            self._active_operations[key] += 1
            logger.debug(
                f"Started {operation_type} for {user_id}. Active: {self._active_operations[key]}"
            )

    def end_operation(self, user_id: str, operation_type: str) -> None:
        """Mark end of an operation (decrements counter).

        Args:
            user_id: User identifier
            operation_type: Type of operation
        """
        with self._lock:
            key = (user_id, operation_type)
            if self._active_operations[key] > 0:
                self._active_operations[key] -= 1
                logger.debug(
                    f"Ended {operation_type} for {user_id}. Active: {self._active_operations[key]}"
                )

    def check_ingestion_limit(self, user_id: str) -> bool:
        """Check hourly ingestion limit.

        Args:
            user_id: User identifier

        Returns:
            True if allowed, False if rate limited
        """
        return self.check_operation_limit(
            user_id, "ingestion", self.config.ingestion_per_hour, 3600
        )

    def check_ingestion_concurrent(self, user_id: str) -> bool:
        """Check concurrent ingestion limit.

        Args:
            user_id: User identifier

        Returns:
            True if allowed, False if rate limited
        """
        return self.check_concurrent_limit(
            user_id, "ingestion", self.config.max_concurrent_ingestions
        )

    def check_embedding_limit(self, user_id: str) -> bool:
        """Check embedding calls per minute limit.

        Args:
            user_id: User identifier

        Returns:
            True if allowed, False if rate limited
        """
        return self.check_operation_limit(
            user_id, "embedding", self.config.embedding_calls_per_minute, 60
        )

    def check_query_limit(self, user_id: str) -> bool:
        """Check query calls per minute limit.

        Args:
            user_id: User identifier

        Returns:
            True if allowed, False if rate limited
        """
        return self.check_operation_limit(
            user_id, "query", self.config.query_calls_per_minute, 60
        )

    def check_file_size(self, size_mb: float) -> bool:
        """Check if file size is within limits.

        Args:
            size_mb: File size in MB

        Returns:
            True if size is acceptable
        """
        if size_mb > self.config.max_file_size_mb:
            logger.warning(
                f"File size {size_mb}MB exceeds limit of {self.config.max_file_size_mb}MB"
            )
            return False
        return True

    def get_operation_count(
        self, user_id: str, operation_type: str, window_seconds: int
    ) -> int:
        """Get count of operations in specified window.

        Args:
            user_id: User identifier
            operation_type: Type of operation
            window_seconds: Time window in seconds

        Returns:
            Number of operations in window
        """
        with self._lock:
            key = (user_id, operation_type)
            now = time.time()
            cutoff_time = now - window_seconds

            return len([ts for ts in self._operation_history[key] if ts > cutoff_time])

    def get_active_count(self, user_id: str, operation_type: str) -> int:
        """Get count of active operations.

        Args:
            user_id: User identifier
            operation_type: Type of operation

        Returns:
            Number of active operations
        """
        with self._lock:
            key = (user_id, operation_type)
            return self._active_operations[key]

    def reset_user(self, user_id: str) -> None:
        """Reset all limits for a user (admin function).

        Args:
            user_id: User identifier
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._operation_history if key[0] == user_id
            ]
            for key in keys_to_remove:
                del self._operation_history[key]
                if key in self._active_operations:
                    del self._active_operations[key]
            logger.info(f"Reset rate limits for user {user_id}")


# Global rate limiter instance
_global_limiter: OperationRateLimiter = OperationRateLimiter(RateLimitConfig())


def get_rate_limiter() -> OperationRateLimiter:
    """Get global rate limiter instance.

    Returns:
        OperationRateLimiter instance
    """
    return _global_limiter


def set_rate_limiter(limiter: OperationRateLimiter) -> None:
    """Set global rate limiter instance (for testing).

    Args:
        limiter: OperationRateLimiter instance
    """
    global _global_limiter
    _global_limiter = limiter
