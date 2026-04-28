# Sprint 4 — Tests

**Plan:** docs/plans/plan_13/OVERVIEW.md
**Wave:** 4 of 4
**Must complete before:** nothing (final wave)

---

## Agent A: T6 — Telemetry Tests

**Complexity:** M
**Estimated time:** 1 hr
**Files to create:**
- `tests/unit/test_telemetry.py` (NEW)

**Depends on:** T1, T2, T4
**Blocks:** none

**Instructions:**

Create `tests/unit/test_telemetry.py` with these test classes:

```python
class TestTelemetryStore:
    # test_creates_db_and_table — init store, verify .db file exists
    # test_log_inserts_row — log an entry, query it back
    # test_get_estimates_returns_stats — log 10 entries, verify avg/p50/p95
    # test_get_estimates_empty — no data returns empty dict
    # test_query_select_works — raw SELECT returns rows
    # test_query_rejects_non_select — DELETE/INSERT raises ValueError
    # test_disabled_store_noop — enabled=False, log() does nothing, query returns empty

class TestTimedDecorator:
    # test_measures_duration — decorate a sleep(0.01) function, verify log entry has duration > 0
    # test_logs_failure — decorate a function that raises, verify success=False logged

class TestMCPTelemetryTools:
    # test_get_estimate_with_data — log entries, call get_estimate, verify response
    # test_get_estimate_no_data — call get_estimate for unknown tool, verify estimate=None
    # test_query_telemetry_select — call query_telemetry with valid SELECT
    # test_query_telemetry_rejects_delete — call with DELETE, verify error
```

Use `tmp_path` fixture for the SQLite database path. Each test gets a fresh store.

**Definition of Done:**
- [ ] All tests pass
- [ ] Covers: store CRUD, estimates, query safety, decorator, disabled mode, MCP tools
- [ ] No regressions in existing tests
