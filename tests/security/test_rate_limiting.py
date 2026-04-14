"""Security tests for operation-specific rate limiting (CWE-770)."""

import time

import pytest

from utils.rate_limiting import (
    OperationRateLimiter,
    RateLimitConfig,
)


class TestRateLimitConfiguration:
    """Tests for RateLimitConfig."""

    def test_default_config_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.ingestion_per_hour == 10
        assert config.max_file_size_mb == 100
        assert config.max_concurrent_ingestions == 2
        assert config.embedding_calls_per_minute == 100
        assert config.pdf_pages_per_hour == 1000
        assert config.query_calls_per_minute == 60

    def test_custom_config_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            ingestion_per_hour=5,
            max_file_size_mb=50,
            max_concurrent_ingestions=1,
        )

        assert config.ingestion_per_hour == 5
        assert config.max_file_size_mb == 50
        assert config.max_concurrent_ingestions == 1


class TestOperationLimitTracking:
    """Tests for operation limit tracking with sliding window."""

    def test_allows_operations_within_limit(self):
        """Test that operations within limit are allowed."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Should allow first 10 ingestions
        for _i in range(10):
            assert limiter.check_operation_limit("user1", "ingestion", 10, 3600)

    def test_rejects_operations_exceeding_limit(self):
        """Test that operations exceeding limit are rejected."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Allow 10 operations
        for _i in range(10):
            assert limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        # 11th should fail
        assert not limiter.check_operation_limit("user1", "ingestion", 10, 3600)

    def test_different_users_independent(self):
        """Test that different users have independent limits."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # User1 reaches limit
        for _i in range(10):
            assert limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        # User1 is rate limited
        assert not limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        # But user2 is not
        assert limiter.check_operation_limit("user2", "ingestion", 10, 3600)

    def test_different_operation_types_independent(self):
        """Test that different operation types have independent limits."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Max out ingestion
        for _i in range(10):
            assert limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        # But embedding is still allowed
        assert limiter.check_operation_limit("user1", "embedding", 100, 60)

    def test_sliding_window_expiration(self):
        """Test that operations expire from sliding window."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Record 5 operations immediately
        for _i in range(5):
            assert limiter.check_operation_limit("user1", "test", 5, 1)

        # Next operation should fail (at limit)
        assert not limiter.check_operation_limit("user1", "test", 5, 1)

        # Wait for window to expire
        time.sleep(1.1)

        # Now it should work again
        assert limiter.check_operation_limit("user1", "test", 5, 1)

    def test_operation_count_tracking(self):
        """Test getting count of operations in window."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        assert limiter.get_operation_count("user1", "ingestion", 3600) == 0

        limiter.check_operation_limit("user1", "ingestion", 100, 3600)
        assert limiter.get_operation_count("user1", "ingestion", 3600) == 1

        limiter.check_operation_limit("user1", "ingestion", 100, 3600)
        assert limiter.get_operation_count("user1", "ingestion", 3600) == 2


class TestConcurrentOperationLimiting:
    """Tests for concurrent operation limits."""

    def test_allows_concurrent_operations_within_limit(self):
        """Test that concurrent operations within limit are allowed."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        assert limiter.check_concurrent_limit("user1", "ingestion", 2)
        assert limiter.check_concurrent_limit("user1", "ingestion", 2)

    def test_rejects_concurrent_operations_exceeding_limit(self):
        """Test that concurrent operations exceeding limit are rejected."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Start first operation
        assert limiter.check_concurrent_limit("user1", "ingestion", 2)
        limiter.start_operation("user1", "ingestion")

        # Start second operation
        assert limiter.check_concurrent_limit("user1", "ingestion", 2)
        limiter.start_operation("user1", "ingestion")

        # Third should be rejected
        assert not limiter.check_concurrent_limit("user1", "ingestion", 2)

        # After ending one, next is allowed
        limiter.end_operation("user1", "ingestion")
        assert limiter.check_concurrent_limit("user1", "ingestion", 2)

    def test_active_operation_tracking(self):
        """Test tracking of active operations."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        assert limiter.get_active_count("user1", "ingestion") == 0

        limiter.start_operation("user1", "ingestion")
        assert limiter.get_active_count("user1", "ingestion") == 1

        limiter.start_operation("user1", "ingestion")
        assert limiter.get_active_count("user1", "ingestion") == 2

        limiter.end_operation("user1", "ingestion")
        assert limiter.get_active_count("user1", "ingestion") == 1

    def test_operation_start_end_cleanup(self):
        """Test that starting/ending operations properly updates counters."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Start operation
        assert limiter.check_concurrent_limit("user1", "test", 2)
        limiter.start_operation("user1", "test")

        # Should reject if we try to check again
        assert limiter.check_concurrent_limit("user1", "test", 1) is False

        # After ending, should allow again
        limiter.end_operation("user1", "test")
        assert limiter.check_concurrent_limit("user1", "test", 2)


class TestFileSizeValidation:
    """Tests for file size validation."""

    def test_allows_small_files(self):
        """Test that small files are allowed."""
        config = RateLimitConfig(max_file_size_mb=100)
        limiter = OperationRateLimiter(config)

        assert limiter.check_file_size(50)
        assert limiter.check_file_size(100)

    def test_rejects_oversized_files(self):
        """Test that oversized files are rejected."""
        config = RateLimitConfig(max_file_size_mb=100)
        limiter = OperationRateLimiter(config)

        assert not limiter.check_file_size(101)
        assert not limiter.check_file_size(500)


class TestConvenienceMethods:
    """Tests for convenience limit checking methods."""

    def test_ingestion_limit(self):
        """Test ingestion-specific limit checking."""
        config = RateLimitConfig(ingestion_per_hour=2)
        limiter = OperationRateLimiter(config)

        assert limiter.check_ingestion_limit("user1")
        assert limiter.check_ingestion_limit("user1")
        assert not limiter.check_ingestion_limit("user1")

    def test_ingestion_concurrent_limit(self):
        """Test ingestion-specific concurrent limit."""
        config = RateLimitConfig(max_concurrent_ingestions=1)
        limiter = OperationRateLimiter(config)

        assert limiter.check_ingestion_concurrent("user1")
        limiter.start_operation("user1", "ingestion")

        assert not limiter.check_ingestion_concurrent("user1")

        limiter.end_operation("user1", "ingestion")
        assert limiter.check_ingestion_concurrent("user1")

    def test_embedding_limit(self):
        """Test embedding-specific limit checking."""
        config = RateLimitConfig(embedding_calls_per_minute=2)
        limiter = OperationRateLimiter(config)

        assert limiter.check_embedding_limit("user1")
        assert limiter.check_embedding_limit("user1")
        assert not limiter.check_embedding_limit("user1")

    def test_query_limit(self):
        """Test query-specific limit checking."""
        config = RateLimitConfig(query_calls_per_minute=2)
        limiter = OperationRateLimiter(config)

        assert limiter.check_query_limit("user1")
        assert limiter.check_query_limit("user1")
        assert not limiter.check_query_limit("user1")


class TestUserReset:
    """Tests for resetting user limits."""

    def test_reset_user_clears_limits(self):
        """Test that resetting a user clears their limits."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # User hits limit
        for _i in range(10):
            limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        assert not limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        # Reset user
        limiter.reset_user("user1")

        # Limits should be cleared
        assert limiter.check_operation_limit("user1", "ingestion", 10, 3600)

    def test_reset_user_only_affects_target_user(self):
        """Test that resetting one user doesn't affect others."""
        config = RateLimitConfig()
        limiter = OperationRateLimiter(config)

        # Both users hit limits
        for user in ["user1", "user2"]:
            for _i in range(10):
                limiter.check_operation_limit(user, "ingestion", 10, 3600)

        # Reset only user1
        limiter.reset_user("user1")

        # user1 limits cleared
        assert limiter.check_operation_limit("user1", "ingestion", 10, 3600)

        # user2 limits still active
        assert not limiter.check_operation_limit("user2", "ingestion", 10, 3600)


class TestIntegrationScenarios:
    """Integration tests for realistic rate limiting scenarios."""

    def test_realistic_ingestion_workflow(self):
        """Test realistic ingestion workflow with rate limits."""
        config = RateLimitConfig(
            ingestion_per_hour=5,
            max_concurrent_ingestions=2,
            max_file_size_mb=50,
        )
        limiter = OperationRateLimiter(config)

        # User tries to upload files
        for file_num in range(5):
            # Check hourly limit
            if not limiter.check_ingestion_limit("user1"):
                pytest.fail(f"File {file_num} rejected by hourly limit")

            # Check concurrent limit
            if not limiter.check_ingestion_concurrent("user1"):
                pytest.fail(f"File {file_num} rejected by concurrent limit")

            # Check file size
            file_size_mb = 30 + file_num
            if not limiter.check_file_size(file_size_mb):
                pytest.fail(f"File {file_num} ({file_size_mb}MB) rejected as too large")

            # Start operation
            limiter.start_operation("user1", "ingestion")

            # Simulate processing...
            time.sleep(0.01)

            # End operation
            limiter.end_operation("user1", "ingestion")

        # Next ingestion should be rate limited (hourly)
        assert not limiter.check_ingestion_limit("user1")

    def test_multi_user_rate_limiting(self):
        """Test rate limiting with multiple users."""
        config = RateLimitConfig(ingestion_per_hour=3)
        limiter = OperationRateLimiter(config)

        users = ["user1", "user2", "user3"]

        # Each user does 3 ingestions (at limit)
        for user in users:
            for _i in range(3):
                assert limiter.check_ingestion_limit(user)

            # Each user should now be rate limited
            assert not limiter.check_ingestion_limit(user)

        # But different users still have their own limits
        for user in users:
            assert not limiter.check_ingestion_limit(user)
