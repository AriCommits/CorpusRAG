# Plan 18 — Parallel Work Coordination Guide

## File Dependency Matrix

```
                              │ C1  C2  C3  C4  C5  C6  C7  C8  C9  C10 C11 C12 C13 C14 D1
──────────────────────────────┼──────────────────────────────────────────────────────────────
src/cli.py                    │ ██  .   .   .   .   .   .   .   ██  .   .   .   .   .   ██
src/tools/__init__.py         │ ██  .   .   .   .   .   .   .   .   .   .   .   .   .   ██
src/tools/cli.py              │ ██  .   .   .   .   .   .   .   .   .   .   .   .   .   ██
src/tools/learning/__init__.py│ .   ██  .   .   .   .   .   .   .   .   .   .   .   .   ██
src/tools/learning/cli.py     │ .   ██  .   .   .   .   .   .   .   .   .   .   .   .   ██
src/tools/flashcards/cli.py   │ .   ██  .   .   .   .   .   .   .   .   .   .   .   .   ██
src/tools/quizzes/cli.py      │ .   ██  .   .   .   .   .   .   .   .   .   .   .   .   ██
src/db/collections_cli.py     │ .   .   ██  ██  .   .   .   .   .   .   .   .   ██  .   ██
src/db/management.py          │ .   .   .   .   ██  ██  ██  ██  .   .   .   .   .   .   ██
src/tools/rag/cli.py          │ .   .   .   .   .   .   .   .   ██  ██  .   .   ██  .   ██
src/tools/rag/tui.py          │ .   .   .   .   .   .   .   .   .   ██  ██  ██  .   ██  ██
src/tools/rag/tui_collections │ .   .   ██  .   .   .   .   .   .   .   .   ██  .   .   ██
src/tools/rag/doctor.py       │ .   .   .   .   .   .   .   .   ██  .   .   .   .   .   ██
src/tools/rag/ingest.py       │ .   .   .   .   .   .   .   ██  .   .   .   .   ██  .   ██
src/CLI.md                    │ .   .   .   .   .   .   .   .   .   .   .   .   .   .   ██
```

## Wave Execution Plan

```
┌─────────────────────────────────────────────────────────────────┐
│ WAVE 1 (Sprint 1) — ~2h                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │ Agent A  │ │ Agent B  │ │ Agent C  │ │ Agent D  │           │
│ │ C1: CLI  │ │ C3: Dead │ │ C5: HTTP │ │ C11: Key │           │
│ │ Restruct │ │ Code Rm  │ │ Logging  │ │ Bindings │           │
│ │ (2h)     │ │ (1h)     │ │ (0.5h)   │ │ (1h)     │           │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ WAVE 2 (Sprint 2) — ~2.5h                                      │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │ Agent A  │ │ Agent B  │ │ Agent C  │ │ Agent D  │           │
│ │ C2: Lrn  │ │ C4: Info │ │ C6: JSON │ │ C10: UI  │           │
│ │ Group    │ │ Fix      │ │ Srlz Fix │ │ Optional │           │
│ │ (1h)     │ │ (1h)     │ │ (2h)     │ │ (2.5h)   │           │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ WAVE 3 (Sprint 3) — ~2h                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                         │
│ │ Agent A  │ │ Agent B  │ │ Agent C  │                         │
│ │ C7: Bkup │ │ C9: Doc  │ │ C12: TUI │                         │
│ │ Consolid │ │ Promote  │ │ Exit Fix │                         │
│ │ (1h)     │ │ (1h)     │ │ (2h)     │                         │
│ └──────────┘ └──────────┘ └──────────┘                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ WAVE 4 (Sprint 4) — ~1.5h                                      │
│ ┌──────────┐ ┌──────────┐                                      │
│ │ Agent A  │ │ Agent B  │                                      │
│ │ C8: Emb  │ │ C14: Col │                                      │
│ │ Metadata │ │ in TUI   │                                      │
│ │ (1.5h)   │ │ (1h)     │                                      │
│ └──────────┘ └──────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ WAVE 5 (Sprint 5) — ~2h                                        │
│ ┌──────────┐                                                    │
│ │ Agent A  │                                                    │
│ │ C13: Ing │                                                    │
│ │ Path Str │                                                    │
│ │ (2h)     │                                                    │
│ └──────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ WAVE 6 (Sprint 6) — ~2h                                        │
│ ┌──────────┐                                                    │
│ │ Agent A  │                                                    │
│ │ D1: Docs │                                                    │
│ │ Scaffold │                                                    │
│ │ (2h)     │                                                    │
│ └──────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Conflict Table

| Task | Conflicts With | Safe to run with |
|------|----------------|-----------------|
| C1   | C9 (cli.py)    | C3, C5, C11 |
| C2   | none in wave   | C4, C6, C10 |
| C3   | C4, C13 (collections_cli.py); C12 (tui_collections.py) | C1, C5, C11 |
| C4   | C3, C13 (collections_cli.py) | C2, C6, C10 |
| C5   | C6, C7, C8 (management.py) | C1, C3, C11 |
| C6   | C5, C7, C8 (management.py) | C2, C4, C10 |
| C7   | C5, C6, C8 (management.py) | C9, C12 |
| C8   | C5, C6, C7 (management.py); C13 (ingest.py) | C14 |
| C9   | C1 (cli.py); C10, C13 (rag/cli.py) | C7, C12 |
| C10  | C9, C13 (rag/cli.py); C11, C12, C14 (tui.py) | C2, C4, C6 |
| C11  | C10, C12, C14 (tui.py) | C1, C3, C5 |
| C12  | C10, C11, C14 (tui.py); C3 (tui_collections.py) | C7, C9 |
| C13  | C8 (ingest.py); C9, C10 (rag/cli.py); C3, C4 (collections_cli.py) | — |
| C14  | C10, C11, C12 (tui.py) | C8 |
| D1   | all files | — (runs last) |

## Integration Workflow

```bash
# After Wave 1 completes
git checkout main
git merge agent-a-sprint1 --no-commit  # C1
git merge agent-b-sprint1 --no-commit  # C3
git merge agent-c-sprint1 --no-commit  # C5
git merge agent-d-sprint1 --no-commit  # C11
pytest tests/
git commit -m "Wave 1: CLI restructure, dead code removal, HTTP logging, TUI keybindings"

# After Wave 2 completes
git merge agent-a-sprint2 --no-commit  # C2
git merge agent-b-sprint2 --no-commit  # C4
git merge agent-c-sprint2 --no-commit  # C6
git merge agent-d-sprint2 --no-commit  # C10
pytest tests/
git commit -m "Wave 2: Learning group, collections fix, JSON serialization, optional collection"

# After Wave 3 completes
git merge agent-a-sprint3 --no-commit  # C7
git merge agent-b-sprint3 --no-commit  # C9
git merge agent-c-sprint3 --no-commit  # C12
pytest tests/
git commit -m "Wave 3: Backup consolidation, doctor promotion, TUI exit fix"

# After Wave 4 completes
git merge agent-a-sprint4 --no-commit  # C8
git merge agent-b-sprint4 --no-commit  # C14
pytest tests/
git commit -m "Wave 4: Export metadata, collections in RAG TUI"

# After Wave 5 completes
git merge agent-a-sprint5 --no-commit  # C13
pytest tests/
git commit -m "Wave 5: Ingest path storage and sync default"

# After Wave 6 completes
git merge agent-a-sprint6 --no-commit  # D1
pytest tests/
git commit -m "Wave 6: Documentation scaffolding"
```

## Recommended Agent Assignments

### 2-Agent Schedule

| Agent | Sequence | Est. Duration |
|-------|----------|---------------|
| Agent 1 | C1 → C2 → C7 → C8 → C13 → D1 | ~10h |
| Agent 2 | C3 → C5 → C6 → C4 → C11 → C10 → C9 → C12 → C14 | ~12h |

**Total estimated duration:** ~12h (bottleneck on Agent 2)

### 3-Agent Schedule

| Agent | Sequence | Est. Duration |
|-------|----------|---------------|
| Agent 1 | C1 → C2 → C9 → D1 | ~6h |
| Agent 2 | C5 → C6 → C7 → C8 → C13 | ~7h |
| Agent 3 | C3 → C4 → C11 → C10 → C12 → C14 | ~8.5h |

**Total estimated duration:** ~8.5h (bottleneck on Agent 3)
