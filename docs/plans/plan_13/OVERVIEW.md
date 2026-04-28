# Plan 13: Execution Telemetry for Agentic Time Estimation

## Summary

Add a persistent SQLite-based telemetry system that logs wall-clock execution times for every MCP tool invocation and RAG pipeline operation. Expose this data back to agents via new MCP tools (`get_estimate` and `query_telemetry`) so they can make data-backed time estimates instead of hallucinating durations.

## Goals

- Log execution time, input size, and result metadata for every tool call
- Store telemetry in a local SQLite database (zero external deps)
- Expose `get_estimate` MCP tool: "How long will ingesting 50 markdown files take?" → looks up historical averages
- Expose `query_telemetry` MCP tool: raw SQL access to telemetry data for advanced queries
- Integrate with existing `RAGBenchmarker` so current benchmarking data flows into the same store
- Respect `telemetry.enabled: false` config — when disabled, nothing is logged

## Non-Goals

- OpenTelemetry/Jaeger integration (already exists as optional extra, separate concern)
- Predicting LLM token generation speed (model-dependent, not our problem)
- Distributed tracing across multiple services

## Background / Context

The existing `utils/benchmarking.py` has an in-memory `RAGBenchmarker` that records retrieval/generation/total times but loses everything when the process exits. The `agent.py` already calls `benchmarker.record()` after every query. The telemetry config section exists (`telemetry.enabled`) but does nothing beyond the setup wizard.

The MCP server now has a clean profile system (Plan 9) where adding new tools is straightforward — create a function in `tools/dev.py`, register it in `profiles.py`.

## Features / Tasks

### T1: Create SQLite telemetry store
**Files:** `src/utils/telemetry.py` (NEW)
**Complexity:** M
**Depends on:** none

Create a `TelemetryStore` class that:
- Opens/creates a SQLite database at a configurable path (default: `.corpusrag/telemetry.db`)
- Creates a `tool_executions` table: `id, tool_name, started_at, duration_ms, input_size_bytes, output_summary, metadata_json, success`
- Provides `log(tool_name, duration_ms, input_size, output_summary, metadata, success)` method
- Provides `get_estimates(tool_name, limit=10)` → returns avg/p50/p95 duration for that tool
- Provides `query(sql, params)` → raw SQL query with parameterized inputs (read-only, SELECT only)
- Thread-safe (uses `threading.Lock` around writes)
- Respects `enabled` flag — when False, all methods are no-ops

### T2: Create telemetry decorator for MCP tools
**Files:** `src/utils/telemetry.py` (append to T1's file)
**Complexity:** S
**Depends on:** T1

Add a `@timed` decorator that wraps any function, measures `time.perf_counter()` duration, and logs to the telemetry store. Also add a `tool_telemetry_wrapper(func, store)` that wraps MCP tool functions specifically — captures input size from args and logs the result.

### T3: Wire telemetry into MCP tool registration
**Files:** `src/mcp_server/profiles.py`, `src/mcp_server/server.py`
**Complexity:** M
**Depends on:** T1, T2

In `server.py`'s `create_mcp_server()`, initialize a `TelemetryStore` based on config. Pass it to `register_profile()`. In `profiles.py`, wrap each tool function with the telemetry decorator so every MCP call is automatically logged.

### T4: Add `get_estimate` and `query_telemetry` MCP tools
**Files:** `src/mcp_server/tools/dev.py`, `src/mcp_server/profiles.py`
**Complexity:** M
**Depends on:** T1, T3

Add two new functions to `dev.py`:
- `get_estimate(tool_name, store)` → returns `{avg_ms, p50_ms, p95_ms, sample_count}` from historical data
- `query_telemetry(sql, store)` → executes read-only SQL against telemetry DB, returns rows

Register both in `profiles.py` under the `dev` profile.

### T5: Migrate RAGBenchmarker to use telemetry store
**Files:** `src/utils/benchmarking.py`, `src/tools/rag/agent.py`
**Complexity:** S
**Depends on:** T1

Update `RAGBenchmarker` to optionally write to the telemetry store in addition to its in-memory list. In `agent.py`, pass the telemetry store to the benchmarker if available. This unifies the existing benchmark data with the new telemetry system.

### T6: Add tests
**Files:** `tests/unit/test_telemetry.py` (NEW)
**Complexity:** M
**Depends on:** T1, T2, T4

Test the telemetry store (create, log, query, estimates), the decorator, the MCP tools, and the disabled-telemetry path.

## New Dependencies

None — SQLite is in the Python standard library.

## File Change Summary

| File | Tasks | Action |
|------|-------|--------|
| `src/utils/telemetry.py` | T1, T2 | NEW |
| `src/mcp_server/profiles.py` | T3, T4 | MODIFY |
| `src/mcp_server/server.py` | T3 | MODIFY |
| `src/mcp_server/tools/dev.py` | T4 | MODIFY |
| `src/utils/benchmarking.py` | T5 | MODIFY |
| `src/tools/rag/agent.py` | T5 | MODIFY |
| `tests/unit/test_telemetry.py` | T6 | NEW |

## Open Questions

- Should `query_telemetry` be restricted to SELECT statements only, or allow any read-only SQL? (Recommendation: SELECT only, enforced by checking the query starts with SELECT)
- Should telemetry DB path be configurable in base.yaml? (Recommendation: yes, under `telemetry.db_path`, default `.corpusrag/telemetry.db`)
