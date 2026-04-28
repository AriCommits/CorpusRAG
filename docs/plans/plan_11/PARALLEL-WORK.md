# Plan 11: Parallel Work Assignments

## File Dependency Matrix

```
                                        │ T1   T2   T3   T4
────────────────────────────────────────┼─────────────────────
tools/rag/pipeline/adaptive_splitter.py │ ██
tools/rag/pipeline/__init__.py          │      ██
tools/rag/config.py                     │      ██
tools/rag/ingest.py                     │      ██
mcp_server/tools/dev.py                 │           ██
setup_wizard.py                         │                ██
tests/unit/test_adaptive_splitter.py    │ ██
tests/unit/test_adaptive_ingest.py      │      ██
```

## Wave Execution Plan

```
Wave 1 (1 agent):     T1: adaptive_splitter.py (NEW file + tests)
                           ↓
Wave 2 (1 agent):     T2: wire into config/ingest
                           ↓
Wave 3 (2 agents):    T3: wire into store_text  ║  T4: setup wizard default
```

## Conflict Table

| Task | Conflicts With | Safe With |
|------|----------------|-----------|
| T1 | — | T3, T4 (but they depend on T2) |
| T2 | — | T3, T4 (but they depend on T2) |
| T3 | — | T4 (different files) |
| T4 | — | T3 (different files) |

## Recommended Execution

**2 agents:**
```
Agent A: T1 → T2 → T3
Agent B: (waits) → T4 (after T2 merges)
```

**1 agent:**
```
T1 → T2 → T3 → T4 (~3 hrs)
```
