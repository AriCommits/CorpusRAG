# PARALLEL-WORK.md — Plan 15 Coordination Guide

**Plan:** Security Hardening
**Total Waves:** 2
**Total Tasks:** 10 (grouped into 8 agent assignments)

---

## File Dependency Matrix

```
                                │ S1  S2  S3  S4  S5  S6  S7  S8  S9  S10
────────────────────────────────┼───────────────────────────────────────────
src/utils/telemetry.py          │ ██
src/mcp_server/tools/dev.py     │     ██              ██
src/tools/video/extractor.py    │         ██
src/tools/video/download.py     │         ██
src/tools/video/ocr.py          │         ██
src/tools/video/ingest.py       │         ██
src/mcp_server/middleware.py    │             ██                  ██
src/config/base.py              │                 ██
src/config/loader.py            │                         ██
src/tools/rag/agent.py          │                             ██
src/tools/video/jobs.py         │                                 ██
src/mcp_server/tools/video.py   │                                 ██
src/tools/rag/pipeline/storage  │                                     ██
tests/unit/test_config.py       │                 ██      ██
tests/unit/test_rag_components  │                             ██      ██
tests/unit/test_mcp_dev_tools   │     ██              ██
```

---

## Conflict Table

| Task | Conflicts With | Resolution |
|------|----------------|------------|
| S2   | S6 (dev.py, test_mcp_dev_tools.py) | Merge into one agent in Wave 2 |
| S4   | S9 (middleware.py) | Merge into one agent in Wave 2 |
| S5   | S7 (test_config.py) | Wave 1 — agents add separate test functions only |
| S8   | S10 (test_rag_components.py) | Wave 1 — agents add separate test functions only |

---

## Wave Execution Plan

```
Wave 1 (Sprint 1) — 6 agents, fully parallel, ~2 hours wall time
┌──────────────────────────────────────────────────────────────────────┐
│  A: S1 SQL injection (1h)    │  B: S3 Video validation (2h)        │
│  C: S5 API key mask (30m)    │  D: S7 Env blocklist (30m)          │
│  E: S8 Prompt injection (1.5h) │  F: S10 Path containment (30m)   │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ merge + verify
Wave 2 (Sprint 2) — 2 agents, parallel, ~2.5 hours wall time
┌──────────────────────────────────────────────────────────────────────┐
│  A: S2+S6 rag_ingest + store_text (1.5h)                            │
│  B: S4+S9 Auth + rate limit + response hardening (2.5h)             │
└──────────────────────────────────────────────────────────────────────┘
```

**Total wall time (3 agents): ~5 hours**
**Total wall time (1 agent, serial): ~10 hours**

---

## Integration Workflow

```bash
# After Wave 1 completes
git checkout feat/plan-15-security-hardening
git merge agent-a-s1-sql --no-ff
git merge agent-b-s3-video --no-ff
git merge agent-c-s5-apikey --no-ff
git merge agent-d-s7-env --no-ff
git merge agent-e-s8-prompt --no-ff
git merge agent-f-s10-path --no-ff
pytest tests/ -x
git tag wave-1-complete

# After Wave 2 completes
git merge agent-a-s2s6-devtools --no-ff
git merge agent-b-s4s9-middleware --no-ff
pytest tests/ -x
git tag plan-15-complete
```

---

## Recommended Agent Assignments

### Schedule: 2 Agents

| Step | Agent 1 | Agent 2 | Wall Time |
|------|---------|---------|-----------|
| W1   | S1 (1h) → S5 (30m) → S7 (30m) | S3 (2h) → S8 (1.5h) → S10 (30m) | 4h |
| W2   | S2+S6 (1.5h) | S4+S9 (2.5h) | 2.5h |
| **Total** | | | **6.5h** |

### Schedule: 3 Agents

| Step | Agent 1 | Agent 2 | Agent 3 | Wall Time |
|------|---------|---------|---------|-----------|
| W1   | S1 (1h) → S5 (30m) | S3 (2h) | S7 (30m) → S8 (1.5h) → S10 (30m) | 2.5h |
| W2   | S2+S6 (1.5h) | S4+S9 (2.5h) | idle | 2.5h |
| **Total** | | | | **5h** |

---

## Severity Coverage

| Wave | Findings Addressed | Severity |
|------|-------------------|----------|
| 1 | C1, H1, H2, H4, H7, M1, M4, M5, M8, L2, L3 | 2 Critical, 3 High, 3 Medium, 2 Low |
| 2 | C2, H3, H5, H6, M2, M3, M6, M7 | 1 Critical, 3 High, 4 Medium |

---

## Summary

| File | Purpose |
|------|---------|
| `docs/plans/plan_15/OVERVIEW.md` | Full plan (10 tasks) |
| `docs/plans/plan_15/PARALLEL-WORK.md` | This coordination guide |
| `docs/plans/plan_15/sprint_1.md` | Wave 1: 6 independent agents |
| `docs/plans/plan_15/sprint_2.md` | Wave 2: 2 agents (merged conflicting tasks) |

- **2 waves total**
- **Wave 1** is fully parallel (6 agents, zero file conflicts on source files; test file conflicts resolved by adding separate functions)
- **Wave 2** has 2 parallel agents (S2+S6 merged, S4+S9 merged to avoid file conflicts)
- **All 17 audit findings addressed** (2 Critical, 7 High, 8 Medium)
- **Suggested starting point:** Wave 1, all 6 agents simultaneously — this alone closes both Criticals and 3 Highs
