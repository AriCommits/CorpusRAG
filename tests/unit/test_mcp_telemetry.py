"""Tests for the MCP log_tool wrapper."""

from unittest.mock import MagicMock

from mcp_server.telemetry import log_tool


def test_log_tool_records_success():
    store = MagicMock()
    result = log_tool(store, "rag_query", lambda: {"status": "success"}, input_size=4)
    assert result["status"] == "success"
    store.log.assert_called_once()
    args, kwargs = store.log.call_args
    assert args[0] == "rag_query"
    assert kwargs["input_size"] == 4
    assert kwargs["success"] is True


def test_log_tool_records_error_status():
    store = MagicMock()
    log_tool(store, "rag_query", lambda: {"status": "error", "error": "nope"})
    assert store.log.call_args.kwargs["success"] is False


def test_log_tool_without_store_is_noop():
    result = log_tool(None, "rag_query", lambda: {"status": "success"})
    assert result["status"] == "success"
