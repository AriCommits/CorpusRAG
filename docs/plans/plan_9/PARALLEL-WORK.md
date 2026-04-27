# Plan 9: Parallel Work Assignments

## File Dependency Matrix

```
                         │ T1   T2   T3   T4   T5   T6   T7   T8
─────────────────────────┼─────────────────────────────────────────
mcp_server/tools/        │
  __init__.py            │ ██
  common.py              │ ██
  dev.py                 │      ██
  learn.py               │           ██
mcp_server/              │
  profiles.py            │                ██
  middleware.py           │                     ██
  server.py              │                          ██
  __init__.py            │                          ██
utils/auth.py            │                     ██
pyproject.toml           │                               ██
README.md                │                               ██
docs/mcp-integration.md  │                               ██
tests/unit/              │
  test_mcp_common.py     │ ██
  test_mcp_dev_tools.py  │      ██
  test_mcp_learn_tools.py│           ██
  test_mcp_profiles.py   │                ██
  test_mcp_server.py     │                          ██
tests/test_mcp_tools.py  │                          ██
tests/integration/       │
  test_mcp_stdio.py      │                                    ██
```

Legend: ██ = Task creates or modifies this file

**Key insight:** T1, T2, T3 all create NEW files with zero overlap. Perfect parallelism.

---

## Parallel Execution Plan

### Wave 1 (Sprint 1) — 3 Agents, Zero Conflicts

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│    AGENT A       │  │    AGENT B       │  │    AGENT C       │
│                  │  │                  │  │                  │
│  T1: common.py   │  │  T2: dev.py      │  │  T3: learn.py    │
│                  │  │                  │  │                  │
│  Creates:        │  │  Creates:        │  │  Creates:        │
│  - tools/common  │  │  - tools/dev     │  │  - tools/learn   │
│  - tools/__init__│  │  - test_dev_tools│  │  - test_learn    │
│  - test_common   │  │                  │  │                  │
│                  │  │  Time: 2 hrs     │  │  Time: 1.5 hrs   │
│  Time: 1 hr     │  │                  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                               │
                          git merge
                               │
                               ▼
```

### Wave 2 (Sprint 2) — 2 Agents, After T1 Merge

```
┌──────────────────┐  ┌──────────────────┐
│    AGENT A       │  │    AGENT B       │
│                  │  │                  │
│  T4: profiles.py │  │  T5: middleware  │
│                  │  │                  │
│  Creates:        │  │  Creates:        │
│  - profiles.py   │  │  - middleware.py │
│  - test_profiles │  │  Modifies:       │
│                  │  │  - utils/auth.py │
│  Imports from:   │  │                  │
│  - tools/common  │  │  Time: 1.5 hrs   │
│  - tools/dev     │  │                  │
│  - tools/learn   │  │                  │
│                  │  │                  │
│  Time: 1.5 hrs   │  │                  │
└──────────────────┘  └──────────────────┘
         │                     │
         └─────────────────────┘
                    │
               git merge
                    │
                    ▼
```

### Wave 3 (Sprint 3) — 2 Agents, After S2 Merge

```
┌──────────────────┐  ┌──────────────────┐
│    AGENT A       │  │    AGENT B       │
│                  │  │                  │
│  T6: server.py   │  │  T7: entrypoints │
│  rewrite         │  │                  │
│                  │  │  Modifies:       │
│  Rewrites:       │  │  - pyproject.toml│
│  - server.py     │  │  - README.md     │
│  - __init__.py   │  │  - mcp docs      │
│  - test_mcp_*    │  │                  │
│                  │  │  Time: 1 hr      │
│  Time: 1.5 hrs   │  │                  │
└──────────────────┘  └──────────────────┘
         │                     │
         └─────────────────────┘
                    │
               git merge
                    │
                    ▼
```

### Wave 4 (Sprint 4) — 1 Agent, Needs Everything

```
┌──────────────────┐
│    AGENT A       │
│                  │
│  T8: E2E test    │
│                  │
│  Creates:        │
│  - test_mcp_stdio│
│                  │
│  Time: 1.5 hrs   │
└──────────────────┘
```

---

## Conflict Table

| Task | Conflicts With | Safe With |
|------|----------------|-----------|
| T1 | — | T2, T3 (all NEW files) |
| T2 | — | T1, T3 (all NEW files) |
| T3 | — | T1, T2 (all NEW files) |
| T4 | T5 (both need T1 merged first) | T5 (different files) |
| T5 | T4 (both need T1 merged first) | T4 (different files) |
| T6 | T7 (both need S2) | T7 (different files) |
| T7 | T6 (both need S2) | T6 (different files) |
| T8 | ALL (needs final code) | None |

---

## Merge Protocol

After each wave:

```bash
# Integration agent workflow
git checkout main
git merge agent-a-branch --no-commit
git merge agent-b-branch --no-commit
# If wave 1: also merge agent-c-branch
pytest tests/ -v --tb=short
git commit -m "Plan 9: Merge Wave N — T[x], T[y]"
```

---

## Recommended Agent Assignments

**If you have 3 agents:**
```
Agent A: T1 → T4 → T6 → T8
Agent B: T2 → T5 → T7
Agent C: T3 → (done, or help with T8 tests)
```

**If you have 2 agents:**
```
Agent A: T1 → T2 → T4 → T6 → T8
Agent B: T3 → T5 → T7
```

**If you have 1 agent:**
```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8
```

---

## Total Estimated Time

| Mode | Wall Clock | Agent Hours |
|------|-----------|-------------|
| 3 agents | ~5 hrs | 12 hrs |
| 2 agents | ~7 hrs | 12 hrs |
| 1 agent | ~12 hrs | 12 hrs |
