# Sprint 2 — Wire Telemetry into MCP + Benchmarker (Parallel)

**Plan:** docs/plans/plan_13/OVERVIEW.md
**Wave:** 2 of 4
**Must complete before:** Sprint 3 (T4 needs profiles.py from T3)

---

## Agent A: T3 — Wire Telemetry into MCP Server

**Complexity:** M
**Estimated time:** 1 hr
**Files to modify:**
- `src/mcp_server/server.py` — init telemetry store in `create_mcp_server()`
- `src/mcp_server/profiles.py` — wrap tool registrations with telemetry

**Depends on:** T1+T2
**Blocks:** T4

**Instructions:**

1. In `server.py`'s `create_mcp_server()`, after `init_db()`, add:
   ```python
   from utils.telemetry import init_telemetry
   telemetry_enabled = config.to_dict().get("telemetry", {}).get("enabled", False)
   store = init_telemetry(enabled=telemetry_enabled)
   ```
   Pass `store` to `register_profile()`.

2. Update `register_profile()` signature to accept `store` parameter.

3. In `profiles.py`, wrap each `@mcp.tool()` function with timing. The simplest approach: measure inside each closure:
   ```python
   @mcp.tool()
   def rag_query(collection: str, query: str, top_k: int = 5) -> dict:
       import time
       start = time.perf_counter()
       result = dev_tools.rag_query(collection, query, top_k, config, db)
       if store:
           store.log("rag_query", (time.perf_counter() - start) * 1000,
                     input_size=len(query), success=result.get("status") == "success")
       return result
   ```

**Definition of Done:**
- [ ] `create_mcp_server()` initializes telemetry store
- [ ] Every MCP tool call logs to telemetry when enabled
- [ ] Telemetry disabled → no logging, no errors
- [ ] Existing MCP tests still pass

---

## Agent B: T5 — Migrate RAGBenchmarker to Telemetry Store

**Complexity:** S
**Estimated time:** 30 min
**Files to modify:**
- `src/utils/benchmarking.py` — add optional telemetry store integration
- `src/tools/rag/agent.py` — pass store to benchmarker

**Depends on:** T1
**Blocks:** none

**Instructions:**

1. In `benchmarking.py`, update `RAGBenchmarker.__init__` to accept optional `telemetry_store`:
   ```python
   def __init__(self, telemetry_store=None):
       self.history = []
       self.telemetry_store = telemetry_store
   ```

2. In `record()`, after appending to history, also log to telemetry:
   ```python
   if self.telemetry_store:
       self.telemetry_store.log("rag_query", result.total_ms, success=True,
                                metadata={"retrieval_ms": result.retrieval_ms,
                                          "generation_ms": result.generation_ms})
   ```

3. In `agent.py`, try to get the global telemetry store and pass it:
   ```python
   from utils.telemetry import get_telemetry_store
   # In __init__ or at module level:
   benchmarker = RAGBenchmarker(telemetry_store=get_telemetry_store())
   ```

**Definition of Done:**
- [ ] `RAGBenchmarker` optionally writes to telemetry store
- [ ] When no store is set, behavior is unchanged
- [ ] Existing benchmark tests still pass
