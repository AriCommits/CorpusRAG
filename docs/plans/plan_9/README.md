# Plan 9: MCP Server Restructure — Profiles, Transports, and Tool Separation

**Status:** Not Started
**Created:** 2026-04-25
**Goal:** Restructure the monolithic MCP server into a clean architecture with profile-based tool loading, stdio+HTTP transport support, and transport-agnostic tool logic.

---

## Problem

The current `mcp_server/server.py` is a 570-line monolith that:
- Fuses all tool domains (RAG, flashcards, quizzes, video) into one file
- Hardcodes FastAPI auth (`Depends()`) into every tool function
- Only supports HTTP transport — unusable with stdio-based editors (Claude, Kiro, OpenCode, Neovim)
- Forces all tools on every user regardless of use case

## Solution

- **Tool profiles:** `--profile dev|learn|full` controls which tools load
- **Transport support:** `--transport stdio|streamable-http` for editors vs cloud
- **Separated layers:** Tool logic in `mcp_server/tools/`, transport/auth in `mcp_server/middleware.py`
- **New `store_text` tool:** Lets agents push context/plans/snippets directly into RAG

---

## Progress Tracker

### Sprint 1 — Tool Extraction (Parallel)

| Task | Status | File | Est. Time | Agent |
|------|--------|------|-----------|-------|
| T1 | [ ] | [S1-T1-common.md](./S1-T1-common.md) | 1 hr | A |
| T2 | [ ] | [S1-T2-dev-tools.md](./S1-T2-dev-tools.md) | 2 hrs | B |
| T3 | [ ] | [S1-T3-learn-tools.md](./S1-T3-learn-tools.md) | 1.5 hrs | C |

### Sprint 2 — Wiring Layer (Parallel after S1-T1)

| Task | Status | File | Est. Time | Agent |
|------|--------|------|-----------|-------|
| T4 | [ ] | [S2-T4-profiles.md](./S2-T4-profiles.md) | 1.5 hrs | A |
| T5 | [ ] | [S2-T5-middleware.md](./S2-T5-middleware.md) | 1.5 hrs | B |

### Sprint 3 — Integration (Serial, needs S1+S2)

| Task | Status | File | Est. Time | Agent |
|------|--------|------|-----------|-------|
| T6 | [ ] | [S3-T6-server-rewrite.md](./S3-T6-server-rewrite.md) | 1.5 hrs | A |
| T7 | [ ] | [S3-T7-entrypoints.md](./S3-T7-entrypoints.md) | 1 hr | B |

### Sprint 4 — Validation (Serial, needs S3)

| Task | Status | File | Est. Time | Agent |
|------|--------|------|-----------|-------|
| T8 | [ ] | [S4-T8-integration.md](./S4-T8-integration.md) | 1.5 hrs | A |

---

## Dependency Graph

```
Sprint 1 (PARALLEL — 3 agents, zero file conflicts):

  T1: common.py ─────┐
  (NEW file)          │
                      ├──→ Sprint 2
  T2: dev.py ─────────┤
  (NEW file)          │
                      │
  T3: learn.py ───────┘
  (NEW file)

Sprint 2 (PARALLEL — 2 agents, after T1 merges):

  T4: profiles.py ────┐
  (NEW, imports T1-T3) │
                       ├──→ Sprint 3
  T5: middleware.py ───┘
  (NEW, refactors auth)

Sprint 3 (PARALLEL — 2 agents, after S2 merges):

  T6: server.py rewrite ──┐
  (REPLACES existing)      ├──→ Sprint 4
  T7: pyproject + docs ────┘
  (config files)

Sprint 4 (SERIAL — needs everything):

  T8: E2E integration test
```

---

## Architecture After Plan 9

```
src/mcp_server/
├── __init__.py              # exports create_mcp_server
├── server.py                # ~80 lines: arg parsing, wiring, mcp.run()
├── profiles.py              # register_dev_tools, register_learn_tools, register_profile
├── middleware.py             # apply_http_middleware (auth, CORS, headers)
└── tools/
    ├── __init__.py
    ├── common.py            # init_config, init_db, validate_query, validate_collection
    ├── dev.py               # rag_ingest, rag_query, rag_retrieve, store_text, list/info collections
    └── learn.py             # flashcards, summaries, quizzes, video tools
```

---

## Session Protocol

### Before Each Task
```bash
git status                    # Confirm clean state
pytest tests/ -v --tb=short   # Baseline green
```

### Starting AI Session
Copy the "Session Prompt" from each task file verbatim.

### After Each Task
```bash
pytest tests/ -v --tb=short   # Still green?
git add -p                    # Stage intentionally
git commit -m "Plan 9 T[N]: brief description"
```

---

## Files Changed (All Tasks)

| File | Tasks | Action |
|------|-------|--------|
| `src/mcp_server/tools/__init__.py` | T1 | NEW |
| `src/mcp_server/tools/common.py` | T1 | NEW |
| `src/mcp_server/tools/dev.py` | T2 | NEW |
| `src/mcp_server/tools/learn.py` | T3 | NEW |
| `src/mcp_server/profiles.py` | T4 | NEW |
| `src/mcp_server/middleware.py` | T5 | NEW |
| `src/mcp_server/server.py` | T6 | REWRITE |
| `src/mcp_server/__init__.py` | T6 | MODIFY |
| `src/utils/auth.py` | T5 | MODIFY (lazy imports) |
| `pyproject.toml` | T7 | MODIFY |
| `README.md` | T7 | MODIFY |
| `docs/mcp-integration.md` | T7 | MODIFY |
| `tests/unit/test_mcp_common.py` | T1 | NEW |
| `tests/unit/test_mcp_dev_tools.py` | T2 | NEW |
| `tests/unit/test_mcp_learn_tools.py` | T3 | NEW |
| `tests/unit/test_mcp_profiles.py` | T4 | NEW |
| `tests/unit/test_mcp_server.py` | T6 | REWRITE |
| `tests/test_mcp_tools.py` | T6 | REWRITE |
| `tests/integration/test_mcp_stdio.py` | T8 | NEW |
