# Sprint 1 — Telemetry Store + Decorator

**Plan:** docs/plans/plan_13/OVERVIEW.md
**Wave:** 1 of 4
**Must complete before:** Sprint 2 (T3, T5 need the store)

---

## Agent A: T1+T2 — Create `utils/telemetry.py`

**Complexity:** M
**Estimated time:** 1.5 hrs
**Files to create:**
- `src/utils/telemetry.py` (NEW)

**Depends on:** none
**Blocks:** T3, T4, T5, T6

**Instructions:**

Create `src/utils/telemetry.py` with:

1. **`TelemetryStore` class:**
   - `__init__(self, db_path=".corpusrag/telemetry.db", enabled=True)` — creates dir, opens SQLite, creates table if not exists
   - Table schema: `tool_executions(id INTEGER PRIMARY KEY AUTOINCREMENT, tool_name TEXT, started_at TEXT, duration_ms REAL, input_size_bytes INTEGER, output_summary TEXT, metadata_json TEXT, success INTEGER)`
   - `log(tool_name, duration_ms, input_size=0, output_summary="", metadata=None, success=True)` — INSERT row. No-op if `enabled=False`.
   - `get_estimates(tool_name, limit=50)` → `{"tool": name, "avg_ms": float, "p50_ms": float, "p95_ms": float, "sample_count": int}`. Returns empty dict if no data.
   - `query(sql, params=())` → executes SELECT-only SQL, returns list of dicts. Raises ValueError if sql doesn't start with SELECT.
   - Thread-safe: use `threading.Lock` around all DB writes.
   - All methods are no-ops returning empty/default values when `enabled=False`.

2. **`timed` decorator:**
   ```python
   def timed(store: TelemetryStore, tool_name: str):
       def decorator(func):
           @functools.wraps(func)
           def wrapper(*args, **kwargs):
               start = time.perf_counter()
               try:
                   result = func(*args, **kwargs)
                   duration = (time.perf_counter() - start) * 1000
                   store.log(tool_name, duration, success=True)
                   return result
               except Exception as e:
                   duration = (time.perf_counter() - start) * 1000
                   store.log(tool_name, duration, success=False, output_summary=str(e))
                   raise
           return wrapper
       return decorator
   ```

3. **Module-level convenience:**
   ```python
   _global_store: TelemetryStore | None = None

   def init_telemetry(db_path=".corpusrag/telemetry.db", enabled=True) -> TelemetryStore:
       global _global_store
       _global_store = TelemetryStore(db_path, enabled)
       return _global_store

   def get_telemetry_store() -> TelemetryStore | None:
       return _global_store
   ```

**Definition of Done:**
- [ ] `TelemetryStore` creates SQLite DB and table
- [ ] `log()` inserts rows, no-ops when disabled
- [ ] `get_estimates()` returns avg/p50/p95 from historical data
- [ ] `query()` only allows SELECT statements
- [ ] `timed` decorator measures and logs execution time
- [ ] Thread-safe writes
- [ ] No external dependencies (stdlib only)
