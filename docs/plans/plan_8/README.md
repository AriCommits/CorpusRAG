# Plan 8: TUI Enhancements & Foundation Fixes

**Status:** In Progress  
**Created:** 2026-04-21  
**Full spec:** [../plan_8.md](../plan_8.md)

---

## Overview

Two tracks of work:
1. **Foundation (A1-A5):** Fix broken generators, wire rate limiting, remove dead code
2. **TUI Features (P1-P6):** Message metadata, context visualization, selective context

---

## Progress Tracker

### Foundation (Do First)

| Task | Status | File | Est. Time |
|------|--------|------|-----------|
| A1 | [ ] | [A1-fix-generators.md](./A1-fix-generators.md) | 2-3 hrs |
| A2 | [ ] | [A2-rate-limiting.md](./A2-rate-limiting.md) | 1-2 hrs |
| A3 | [ ] | [A3-mcp-fixes.md](./A3-mcp-fixes.md) | 30 min |
| A4 | [ ] | [A4-dead-code.md](./A4-dead-code.md) | 1 hr |
| A5 | [ ] | [A5-optional-extras.md](./A5-optional-extras.md) | 1-2 hrs |

### TUI Features (After Foundation)

| Task | Status | File | Est. Time |
|------|--------|------|-----------|
| P1 | [ ] | [P1-message-metadata.md](./P1-message-metadata.md) | 2 hrs |
| P2 | [ ] | [P2-context-sidebar.md](./P2-context-sidebar.md) | 2-3 hrs |
| P3 | [ ] | [P3-selective-context.md](./P3-selective-context.md) | 2 hrs |
| P4 | [ ] | [P4-token-counting.md](./P4-token-counting.md) | 1 hr |
| P5 | [ ] | [P5-security-ux.md](./P5-security-ux.md) | 1-2 hrs |
| P6 | [ ] | [P6-tests.md](./P6-tests.md) | 1-2 hrs |

---

## Dependency Graph

```
A3 (quick fixes) ──┐
                   │
A1 (generators) ───┼──→ A4 (cleanup) ──→ A5 (extras)
                   │
A2 (rate limit) ───┘
                   
         ↓ Foundation Complete ↓

P1 (metadata) ──→ P2 (sidebar) ──→ P3 (selective) ──→ P4 (tokens)
                                                          │
                                                          ↓
                                              P5 (security) ──→ P6 (tests)
```

---

## Recommended Order

**Week 1: Foundation**
1. A3 — Fix MCP attribute errors (quick win, 30 min)
2. A1 — Fix generators (critical, 2-3 hrs)
3. A2 — Wire rate limiting (1-2 hrs)
4. A4 — Remove dead code (1 hr)

**Week 2: TUI Core**
5. P1 — Message metadata + timer (2 hrs)
6. P2 — Context sidebar (2-3 hrs)
7. P3 — Selective context (2 hrs)

**Week 3: Polish**
8. P4 — Token counting (1 hr)
9. P5 — Security & UX (1-2 hrs)
10. P6 — Tests (1-2 hrs)
11. A5 — Optional extras (1-2 hrs, do last)

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
git diff                      # Review changes
pytest tests/ -v --tb=short   # Still green?
# Manual verification per task file
git add -p                    # Stage intentionally
git commit -m "Plan 8 [TASK_ID]: brief description"
```

---

## Files Changed (All Tasks)

| File | Tasks |
|------|-------|
| `src/tools/flashcards/generator.py` | A1 |
| `src/tools/summaries/generator.py` | A1 |
| `src/tools/quizzes/generator.py` | A1 |
| `src/config/base.py` | A2 |
| `src/llm/backend.py` | A2, P4 |
| `src/mcp_server/server.py` | A3 |
| `src/orchestrations/knowledge_base.py` | A3 |
| `src/tools/rag/tui.py` | P1, P2, P3 |
| `src/tools/rag/tui_context.py` | P2, P3 (NEW) |
| `src/tools/rag/agent.py` | P1, P3 |
| `src/tools/rag/session.py` | P3 |
| `src/utils/tokens.py` | P2 (NEW) |
| `pyproject.toml` | A4, A5 |
