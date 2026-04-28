# Sprint 3 — Estimation MCP Tools

**Plan:** docs/plans/plan_13/OVERVIEW.md
**Wave:** 3 of 4
**Must complete before:** Sprint 4 (T6 tests)

---

## Agent A: T4 — Add `get_estimate` and `query_telemetry` MCP Tools

**Complexity:** M
**Estimated time:** 1 hr
**Files to modify:**
- `src/mcp_server/tools/dev.py` — add two new functions
- `src/mcp_server/profiles.py` — register them in dev profile

**Depends on:** T1, T3
**Blocks:** T6

**Instructions:**

1. In `dev.py`, add:

```python
def get_estimate(tool_name: str, store) -> dict:
    """Get time estimate for a tool based on historical execution data."""
    if not store:
        return {"status": "error", "error": "Telemetry is disabled"}
    try:
        estimates = store.get_estimates(tool_name)
        if not estimates:
            return {"status": "success", "tool": tool_name, "estimate": None,
                    "message": f"No historical data for '{tool_name}'"}
        return {"status": "success", **estimates}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def query_telemetry(sql: str, store) -> dict:
    """Execute a read-only SQL query against the telemetry database."""
    if not store:
        return {"status": "error", "error": "Telemetry is disabled"}
    try:
        rows = store.query(sql)
        return {"status": "success", "rows": rows, "count": len(rows)}
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

2. In `profiles.py`'s `register_dev_tools()`, add:

```python
@mcp.tool()
def get_estimate(tool_name: str) -> dict:
    """Get historical time estimate for a tool.

    Returns avg/p50/p95 execution times based on past runs.
    Use this to provide data-backed time estimates instead of guessing.

    Args:
        tool_name: Name of the tool (e.g., "rag_query", "rag_ingest", "store_text").
    """
    return dev_tools.get_estimate(tool_name, store)

@mcp.tool()
def query_telemetry(sql: str) -> dict:
    """Query the telemetry database with read-only SQL.

    Only SELECT statements are allowed. Returns rows as list of dicts.

    Args:
        sql: SQL SELECT query (e.g., "SELECT tool_name, AVG(duration_ms) FROM tool_executions GROUP BY tool_name").
    """
    return dev_tools.query_telemetry(sql, store)
```

**Definition of Done:**
- [ ] `get_estimate("rag_query")` returns avg/p50/p95 from historical data
- [ ] `get_estimate("nonexistent")` returns `estimate: None` with helpful message
- [ ] `query_telemetry("SELECT ...")` returns rows
- [ ] `query_telemetry("DELETE ...")` returns error
- [ ] Both tools appear in `dev` and `full` profiles
- [ ] Telemetry disabled → both return clear error
