# PARALLEL-WORK.md — Plan 17 Coordination Guide

**Plan:** Live Config Integration Tests
**Total Waves:** 1
**Total Tasks:** 6 (grouped into 5 agent assignments)

---

## File Dependency Matrix

```
                              │ T1  T2  T3  T4  T5  T6
──────────────────────────────┼─────────────────────────
tests/live/__init__.py        │ ██
tests/live/conftest.py        │ ██
tests/live/test_chromadb.py   │     ██
tests/live/test_ollama.py     │         ██
tests/live/test_rag_pipeline  │             ██
src/tools/rag/doctor.py       │                 ██
src/tools/rag/cli.py          │                 ██
pyproject.toml                │ ██
```

Zero file conflicts between any tasks.

---

## Wave Execution Plan

```
Wave 1 — All 5 agents in parallel, ~1.5 hours wall time
┌──────────────────────────────────────────────────────────────────────┐
│  A: T1+T6 Fixtures+Config (1h)  │  B: T2 ChromaDB tests (30m)      │
│  C: T3 Ollama tests (30m)       │  D: T4 RAG pipeline test (1h)    │
│  E: T5 Doctor command (1.5h)    │                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Single wave — everything is parallel.** No serial dependencies because all tasks create new files.

---

## Conflict Table

| Task | Conflicts With | Safe to run with |
|------|----------------|------------------|
| T1   | none           | all |
| T2   | none           | all |
| T3   | none           | all |
| T4   | none           | all |
| T5   | none           | all |
| T6   | none (merged with T1) | all |

---

## Integration Workflow

```bash
# Single wave — merge all agents
git checkout -b feat/plan-17-live-tests
git merge agent-a-fixtures --no-ff
git merge agent-b-chromadb --no-ff
git merge agent-c-ollama --no-ff
git merge agent-d-rag-pipeline --no-ff
git merge agent-e-doctor --no-ff
pytest tests/unit/ -x          # Verify no regressions
pytest -m live                 # Run live tests (requires services)
git tag plan-17-complete
```

---

## Recommended Agent Assignments

### Schedule: 2 Agents

| Agent 1 | Agent 2 | Wall Time |
|---------|---------|-----------|
| T1+T6 (1h) → T4 (1h) | T2 (30m) → T3 (30m) → T5 (1.5h) | 2.5h |

### Schedule: 3 Agents

| Agent 1 | Agent 2 | Agent 3 | Wall Time |
|---------|---------|---------|-----------|
| T1+T6 (1h) | T2 (30m) → T3 (30m) | T5 (1.5h) → T4 (1h) | 2.5h |

---

## How to Run

```bash
# Normal pytest (live tests excluded by default)
pytest

# Run only live tests (requires ChromaDB + Ollama running)
pytest -m live

# Run the doctor command
corpus rag doctor

# Run live tests verbosely
pytest tests/live/ -v --tb=long
```

---

## Summary

| File | Purpose |
|------|---------|
| `docs/plans/plan_17/OVERVIEW.md` | Full plan (6 tasks) |
| `docs/plans/plan_17/PARALLEL-WORK.md` | This coordination guide |
| `docs/plans/plan_17/sprint_1.md` | Wave 1: 5 agents, all parallel |

- **1 wave total** — all tasks are independent
- **Zero file conflicts** — every task creates new files or modifies unique files
- **Suggested starting point:** All agents simultaneously
