# Plan 13: Parallel Work Assignments

## File Dependency Matrix

```
                         │ T1   T2   T3   T4   T5   T6
─────────────────────────┼─────────────────────────────────
utils/telemetry.py       │ ██   ██
mcp_server/profiles.py   │           ██   ██
mcp_server/server.py     │           ██
mcp_server/tools/dev.py  │                ██
utils/benchmarking.py    │                     ██
tools/rag/agent.py       │                     ██
tests/unit/test_telem*   │                          ██
```

## Wave Execution Plan

```
Wave 1 (1 agent, serial — same file):
  T1+T2: telemetry.py (store + decorator)
         ↓

Wave 2 (2 agents, PARALLEL — different files):
  T3: profiles.py + server.py  ║  T5: benchmarking.py + agent.py
         ↓                              (done)

Wave 3 (1 agent, serial — needs T3's profiles.py):
  T4: dev.py + profiles.py (new MCP tools)
         ↓

Wave 4 (1 agent, serial — needs everything):
  T6: tests
```

## Conflict Table

| Task | Conflicts With | Safe With |
|------|----------------|-----------|
| T1 | T2 (same file) | T5 (but T5 depends on T1) |
| T2 | T1 (same file) | T5 (but T5 depends on T1) |
| T3 | T4 (profiles.py) | T5 (different files) |
| T4 | T3 (profiles.py) | T5, T6 |
| T5 | — | T3 (different files) |
| T6 | — | All (but depends on T1+T2+T4) |

## Recommended Agent Assignments

**2 agents:**
```
Agent A: T1+T2 → T3 → T4 → T6
Agent B: (wait for T1) → T5
Total: ~4 hrs wall clock
```

**1 agent:**
```
T1 → T2 → T3 → T5 → T4 → T6
Total: ~5 hrs
```
