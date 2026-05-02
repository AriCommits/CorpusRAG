# PARALLEL-WORK.md — Plan 14 Coordination Guide

**Plan:** Video Ingestion Pipeline + MCP Tools
**Total Waves:** 4
**Total Tasks:** 11

---

## File Dependency Matrix

```
                              │ V1  V2  V3  V4  V5  V6  V7  V8  V9  V10 V11
──────────────────────────────┼─────────────────────────────────────────────────
src/tools/video/extractor.py  │ ██                  ██
src/tools/video/classifier.py │     ██              ██
src/tools/video/ocr.py        │         ██          ██
src/tools/video/postprocessor │             ██      ██
src/tools/video/jobs.py       │                 ██          ██
src/tools/video/ingest.py     │                     ██      ██  ██
src/tools/video/download.py   │                         ██  ██  ██
src/tools/video/config.py     │                             ██      ██
src/tools/video/cli.py        │                                     ██
src/mcp_server/tools/video.py │                             ██
src/mcp_server/profiles.py    │                             ██
configs/base.yaml             │                             ██
pyproject.toml                │                                         ██
README.md                     │                                         ██
src/CLI.md                    │                                         ██
src/mcp_server/README.md      │                                         ██
```

---

## Wave Execution Plan

```
Wave 1 (Sprint 1) ─ All parallel, ~3 hours wall time
┌─────────────────────────────────────────────────────────────────────┐
│  A: V1 Extractor (2h)  │  B: V2 Classifier (1h)  │  C: V3 OCR (3h)│
│  D: V4 PostProc (1h)   │  E: V5 Jobs (2h)        │  F: V7 DL (1h) │
│  G: V8 Config (1h)     │                          │                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ merge + verify
Wave 2 (Sprint 2) ─ Single agent, ~3 hours
┌─────────────────────────────────────────────────────────────────────┐
│  A: V6 Orchestrator (3h)                                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ merge + verify
Wave 3 (Sprint 3) ─ Two agents in parallel, ~3 hours wall time
┌─────────────────────────────────────────────────────────────────────┐
│  A: V9 MCP Tools (3h)             │  B: V10 CLI (2h)               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ merge + verify
Wave 4 (Sprint 4) ─ Single agent, ~1 hour
┌─────────────────────────────────────────────────────────────────────┐
│  A: V11 Docs (1h)                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

**Total wall time (3 agents): ~10 hours**
**Total wall time (1 agent, serial): ~20 hours**

---

## Conflict Table

| Task | Conflicts With | Safe to run with |
|------|----------------|------------------|
| V1   | none           | V2, V3, V4, V5, V7, V8 |
| V2   | none           | V1, V3, V4, V5, V7, V8 |
| V3   | none           | V1, V2, V4, V5, V7, V8 |
| V4   | none           | V1, V2, V3, V5, V7, V8 |
| V5   | none           | V1, V2, V3, V4, V7, V8 |
| V6   | none in wave   | — (sole task in Wave 2) |
| V7   | none           | V1, V2, V3, V4, V5, V8 |
| V8   | none           | V1, V2, V3, V4, V5, V7 |
| V9   | none           | V10 |
| V10  | none           | V9 |
| V11  | none           | — (sole task in Wave 4) |

No file conflicts exist between any concurrent tasks. All Wave 1 tasks create NEW files. Wave 3 tasks modify different files (V9: profiles.py + new video.py, V10: cli.py).

---

## Integration Workflow

```bash
# After Wave 1 completes (all 7 agents)
git checkout main
git merge agent-a-v1-extractor --no-ff
git merge agent-b-v2-classifier --no-ff
git merge agent-c-v3-ocr --no-ff
git merge agent-d-v4-postprocessor --no-ff
git merge agent-e-v5-jobs --no-ff
git merge agent-f-v7-download --no-ff
git merge agent-g-v8-config --no-ff
pytest tests/ -x
git tag wave-1-complete

# After Wave 2 completes
git merge agent-a-v6-orchestrator --no-ff
pytest tests/ -x
git tag wave-2-complete

# After Wave 3 completes (both agents)
git merge agent-a-v9-mcp --no-ff
git merge agent-b-v10-cli --no-ff
pytest tests/ -x
git tag wave-3-complete

# After Wave 4 completes
git merge agent-a-v11-docs --no-ff
pytest tests/ -x
git tag plan-14-complete
```

---

## Recommended Agent Assignments

### Schedule: 2 Agents

| Step | Agent 1 | Agent 2 | Wall Time |
|------|---------|---------|-----------|
| W1   | V1 (2h) → V3 (3h) → V5 (2h) | V2 (1h) → V4 (1h) → V7 (1h) → V8 (1h) | 7h |
| W2   | V6 (3h) | idle | 3h |
| W3   | V9 (3h) | V10 (2h) | 3h |
| W4   | V11 (1h) | idle | 1h |
| **Total** | | | **14h** |

### Schedule: 3 Agents

| Step | Agent 1 | Agent 2 | Agent 3 | Wall Time |
|------|---------|---------|---------|-----------|
| W1   | V1 (2h) → V5 (2h) | V2 (1h) → V4 (1h) → V8 (1h) | V3 (3h) → V7 (1h) | 4h |
| W2   | V6 (3h) | idle | idle | 3h |
| W3   | V9 (3h) | V10 (2h) | idle | 3h |
| W4   | V11 (1h) | idle | idle | 1h |
| **Total** | | | | **11h** |

---

## Summary

| File | Purpose |
|------|---------|
| `docs/plans/plan_14/OVERVIEW.md` | Full plan (11 tasks) |
| `docs/plans/plan_14/PARALLEL-WORK.md` | This coordination guide |
| `docs/plans/plan_14/sprint_1.md` | Wave 1: 7 foundation components (all parallel) |
| `docs/plans/plan_14/sprint_2.md` | Wave 2: Pipeline orchestrator |
| `docs/plans/plan_14/sprint_3.md` | Wave 3: MCP tools + CLI (parallel) |
| `docs/plans/plan_14/sprint_4.md` | Wave 4: Dependencies + docs |

- **4 waves total**
- **Wave 1** is fully parallel (7 independent tasks, zero file conflicts)
- **Wave 2** is serial (orchestrator depends on all Wave 1 outputs)
- **Wave 3** is parallel (MCP and CLI touch different files)
- **Wave 4** is serial (docs depend on everything)
- **Suggested starting point:** Wave 1, all agents simultaneously
