"""Tests for execution telemetry system."""

import time
import pytest
from utils.telemetry import TelemetryStore, timed


@pytest.fixture()
def store(tmp_path):
    """Create a fresh telemetry store for each test."""
    db_path = str(tmp_path / "test_telemetry.db")
    s = TelemetryStore(db_path=db_path, enabled=True)
    yield s
    s.close()


@pytest.fixture()
def disabled_store(tmp_path):
    """Create a disabled telemetry store."""
    return TelemetryStore(db_path=str(tmp_path / "disabled.db"), enabled=False)


class TestTelemetryStore:
    def test_creates_db_and_table(self, store, tmp_path):
        assert (tmp_path / "test_telemetry.db").exists()

    def test_log_inserts_row(self, store):
        store.log("test_tool", 150.5, input_size=100, success=True)
        rows = store.query("SELECT * FROM tool_executions WHERE tool_name = 'test_tool'")
        assert len(rows) == 1
        assert rows[0]["tool_name"] == "test_tool"
        assert rows[0]["duration_ms"] == 150.5

    def test_get_estimates_returns_stats(self, store):
        for i in range(10):
            store.log("bench_tool", 100.0 + i * 10, success=True)
        est = store.get_estimates("bench_tool")
        assert est["tool"] == "bench_tool"
        assert est["sample_count"] == 10
        assert est["avg_ms"] > 0
        assert "p50_ms" in est
        assert "p95_ms" in est

    def test_get_estimates_empty(self, store):
        assert store.get_estimates("nonexistent") == {}

    def test_query_select_works(self, store):
        store.log("q_tool", 50.0)
        rows = store.query("SELECT tool_name, duration_ms FROM tool_executions")
        assert len(rows) == 1
        assert rows[0]["tool_name"] == "q_tool"

    def test_query_rejects_non_select(self, store):
        with pytest.raises(ValueError, match="Only SELECT"):
            store.query("DELETE FROM tool_executions")

    def test_query_rejects_insert(self, store):
        with pytest.raises(ValueError, match="Only SELECT"):
            store.query("INSERT INTO tool_executions (tool_name) VALUES ('hack')")

    def test_disabled_store_log_noop(self, disabled_store):
        disabled_store.log("test", 100.0)  # Should not raise

    def test_disabled_store_query_empty(self, disabled_store):
        assert disabled_store.query("SELECT 1") == []

    def test_disabled_store_estimates_empty(self, disabled_store):
        assert disabled_store.get_estimates("test") == {}


class TestTimedDecorator:
    def test_measures_duration(self, store):
        @timed(store, "sleep_tool")
        def slow_func():
            time.sleep(0.02)
            return "done"

        result = slow_func()
        assert result == "done"
        rows = store.query("SELECT * FROM tool_executions WHERE tool_name = 'sleep_tool'")
        assert len(rows) == 1
        assert rows[0]["duration_ms"] >= 15  # at least 15ms
        assert rows[0]["success"] == 1

    def test_logs_failure(self, store):
        @timed(store, "fail_tool")
        def bad_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            bad_func()

        rows = store.query("SELECT * FROM tool_executions WHERE tool_name = 'fail_tool'")
        assert len(rows) == 1
        assert rows[0]["success"] == 0
        assert "boom" in rows[0]["output_summary"]


class TestMCPTelemetryTools:
    def test_get_estimate_with_data(self, store):
        from mcp_server.tools.dev import get_estimate
        for _ in range(5):
            store.log("rag_query", 200.0, success=True)
        result = get_estimate("rag_query", store)
        assert result["status"] == "success"
        assert result["avg_ms"] == 200.0
        assert result["sample_count"] == 5

    def test_get_estimate_no_data(self, store):
        from mcp_server.tools.dev import get_estimate
        result = get_estimate("unknown_tool", store)
        assert result["status"] == "success"
        assert result["estimate"] is None

    def test_get_estimate_disabled(self):
        from mcp_server.tools.dev import get_estimate
        result = get_estimate("test", None)
        assert result["status"] == "error"

    def test_query_telemetry_select(self, store):
        from mcp_server.tools.dev import query_telemetry
        store.log("test", 100.0)
        result = query_telemetry("SELECT * FROM tool_executions", store)
        assert result["status"] == "success"
        assert result["count"] == 1

    def test_query_telemetry_rejects_delete(self, store):
        from mcp_server.tools.dev import query_telemetry
        result = query_telemetry("DELETE FROM tool_executions", store)
        assert result["status"] == "error"
        assert "SELECT" in result["error"]
