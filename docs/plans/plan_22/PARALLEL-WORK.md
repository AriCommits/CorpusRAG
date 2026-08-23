# PARALLEL-WORK — Plan 22: Kernel API, Simple MCP, First-Run

Coordination guide for executing `docs/plans/plan_22/`.
Source of truth: `OVERVIEW.md`. Per-agent briefs: `sprint_<N>.md`.

Tasks: **K1, H1, F1, G1, K2, K3, D1**

---

## 4a — File Dependency Matrix

`██` = task modifies/creates/deletes this file.

```
                                         │ K1  H1  F1  G1  K2  K3  D1
─────────────────────────────────────────┼───────────────────────────
src/kernel.py                            │ ██              ██  ██
pyproject.toml                           │ ██
tests/test_kernel.py                     │ ██
src/tools/rag/vectorstores/              │     ██
src/tools/rag/README.md                  │     ██
tests/test_dead_code_removal.py          │     ██
src/setup_wizard.py                      │         ██
src/tools/rag/doctor.py                  │         ██
.docker/docker-compose.yml               │         ██
tests/unit/test_setup_wizard_config.py   │         ██
tests/unit/test_doctor.py                │         ██
src/tools/flashcards/generator.py        │             ██
src/tools/quizzes/generator.py           │             ██
src/tools/summaries/generator.py         │             ██
tests/unit/test_generation.py            │             ██
src/cli.py                               │                 ██
src/tools/rag/cli.py                     │                 ██
cli.txt                                  │                 ██
tests/unit/test_kernel_cli.py            │                 ██
src/mcp_server/profiles.py               │                     ██
src/mcp_server/server.py                 │                     ██
src/mcp_server/tools/dev.py              │                     ██
src/mcp_server/tools/learn.py            │                     ██
tests/unit/test_mcp_profiles.py          │                     ██
README.md                                │                         ██
docs/architecture.md                     │                         ██
docs/mcp-integration.md                  │                         ██
docs/tools-usage.md                      │                         ██
docs/troubleshooting.md                  │                         ██
docs/docker-deployment.md                │                         ██
src/CLI.md                               │                         ██
src/mcp_server/README.md                 │                         ██
```

K2/K3 **read** `src/kernel.py` but must not rewrite it; if a tiny export is missing, land it as a K1 follow-up on the same branch before starting Wave 2.

---

## 4b — Wave Execution Plan

```
Wave 1 (parallel)     Wave 2 (parallel, after K1)     Wave 3 (serial)
┌──────────┐          ┌──────────┐                    ┌──────────┐
│ K1 kernel│──┐       │ K2 CLI   │──┐                 │ D1 docs  │
└──────────┘  │       └──────────┘  │                 └──────────┘
┌──────────┐  │       ┌──────────┐  │
│ H1 husk  │  │       │ K3 MCP   │──┘
└──────────┘  │       └──────────┘
┌──────────┐  │
│ F1 first │──┘ (F1 needed by D1 only)
└──────────┘
┌──────────┐
│ G1 gens  │  (independent)
└──────────┘
```

Estimated: Wave 1 ~3h (critical path K1/F1), Wave 2 ~3h, Wave 3 ~2h.

---

## 4c — Conflict Table

| Task | Conflicts With | Safe to run with |
|------|----------------|------------------|
| K1   | none in Wave 1 | H1, F1, G1 |
| H1   | none           | K1, F1, G1 |
| F1   | none           | K1, H1, G1 |
| G1   | none           | K1, H1, F1 |
| K2   | K3 only if someone edits `kernel.py` | K3 if kernel is frozen |
| K3   | K2 only if someone edits `kernel.py` | K2 if kernel is frozen |
| D1   | none once CLI/MCP/wizard strings exist | — (serial last) |

K2 and K3 share no write set if they treat `kernel.py` as read-only.

---

## 4d — Integration Workflow

```bash
# After Wave 1 completes (four agents, or one branch with all four)
git checkout plan-22/sprint-1
# if split: merge agent branches --no-commit, pytest, commit
uv run pytest tests/ -m "not live"
git commit -m "plan_22 sprint 1: kernel, vectorstores husk, first-run, generators"

# After Wave 2
uv run pytest tests/ -m "not live"
git commit -m "plan_22 sprint 2: top-level CLI and simple MCP profile"

# After Wave 3
uv run pytest tests/ -m "not live"
git commit -m "plan_22 sprint 3: kernel, simple MCP, and first-run docs"
```

Single-agent workflow (this repo’s usual pattern): one branch `plan-22/sprint-1`, three commits, no merge trains.

---

## 4e — Recommended Agent Assignments

### 2-agent team

| Agent | Wave 1 | Wave 2 | Wave 3 |
|-------|--------|--------|--------|
| A     | K1 then F1 | K2 | D1 |
| B     | H1 then G1 | K3 | (idle / review) |

### 3-agent team

| Agent | Wave 1 | Wave 2 | Wave 3 |
|-------|--------|--------|--------|
| A     | K1 | K2 | D1 |
| B     | F1 | K3 | review |
| C     | H1 + G1 | idle | review |

### 1-agent team

Sprint 1 (K1, H1, F1, G1) → sprint 2 (K2, K3) → sprint 3 (D1) on `plan-22/sprint-1`.
