# PARALLEL-WORK — Plan 20: CorpusRAG Portfolio Hardening

Coordination guide for executing `docs/plans/plan_20/` in parallel waves.
Source of truth for this effort. See `OVERVIEW.md` for full task detail and `sprint_<N>.md` for
per-agent briefs.

Tasks: **C1, C2, O1, O2, D1, D2, P1, V1**

---

## 4a — File Dependency Matrix

`██` = task modifies/creates/deletes this file.

```
                                    │ C1   C2   O1   O2   D1   D2   P1   V1
────────────────────────────────────┼───────────────────────────────────────
src/config/base.py                  │ ██
configs/base.yaml                   │      ██
configs/rag.yaml                    │      ██
configs/video.yaml                  │      ██
configs/generators.yaml             │      ██
configs/orchestrations.yaml         │      ██
configs/base.example.yaml           │      ██
src/cli.py                          │           ██
src/orchestrations/cli.py           │           ██   ██                        ← shared (O1→O2)
src/orchestrations/study_session.py │           ██                             (delete)
src/orchestrations/knowledge_base.py│           ██                             (delete)
src/orchestrations/__init__.py      │           ██
src/orchestrations/lecture_pipeline.py│              ██
README.md                           │                     ██
src/CLI.md                          │                     ██
cli.txt                             │                     ██
docs/configuration.md               │                          ██
configs/.env.example                │                          ██
pyproject.toml                      │                               ██
.github/workflows/ci.yml            │                               ██
uv.lock                             │                               ██
tests/ (new per-task files)         │ ██   ██   ██   ██                       ██
src/**, tests/** (format sweep)     │                                         ██
```

Only one file is shared between tasks: `src/orchestrations/cli.py` (O1 registers/trims the group;
O2 rewires the `lecture_pipeline` command). This is resolved by ordering O2 after O1 (O2 depends on
O1). V1's `ruff format` sweep can touch any source file, so V1 runs alone in the final wave.

---

## 4b — Wave Execution Plan

```
WAVE 1  (fully parallel — disjoint files)
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Agent A: C1  │ │ Agent B: O1  │ │ Agent C: D2  │ │ Agent D: P1  │
│ config raw   │ │ orchestrate  │ │ config docs  │ │ CI + pkg     │
│ propagation  │ │ wiring + del │ │ + .env       │ │ + uv.lock    │
│ ~2h  (M)     │ │ ~2h  (M)     │ │ ~2h  (M)     │ │ ~3h  (L)     │
└──────┬───────┘ └──────┬───────┘ └──────────────┘ └──────────────┘
       │                │
       │  (C1 → C2,O2)  │  (O1 → O2, D1)
       ▼                ▼
WAVE 2  (fully parallel — disjoint files)
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Agent A: C2  │ │ Agent B: O2  │ │ Agent C: D1  │
│ config split │ │ lecture-pipe │ │ docs/CLI     │
│ + example fix│ │ config wiring│ │ align+primer │
│ ~3h  (M)     │ │ ~3h  (M)     │ │ ~3h  (L)     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
WAVE 3  (serial — single integration agent)
┌───────────────────────────────────────────┐
│ Agent A: V1 — verify, format, consistency  │
│ CLI↔docs tests, ruff format, full CI green  │
│ ~2–3h  (M)                                  │
└───────────────────────────────────────────┘
```

Critical path: **C1 → (C2 ‖ O2) → V1** and **O1 → (O2 ‖ D1) → V1**.
Wall-clock with enough agents ≈ Wave 1 (3h, bounded by P1) + Wave 2 (3h) + Wave 3 (3h) ≈ **~9h**.

---

## 4c — Conflict Table

| Task | Conflicts With | Reason | Safe to run with |
|------|----------------|--------|------------------|
| C1   | none           | sole owner of `src/config/base.py` | O1, D2, P1 |
| O1   | O2 (`src/orchestrations/cli.py`) | both edit the orchestrate CLI file | C1, D2, P1 |
| D2   | none           | sole owner of `docs/configuration.md`, `.env.example` | C1, O1, P1 |
| P1   | none           | sole owner of `pyproject.toml`, `ci.yml`, `uv.lock` | C1, O1, D2 |
| C2   | none (in wave 2) | sole owner of `configs/*.yaml` + `base.example.yaml` | O2, D1 |
| O2   | O1 (prior wave) | shares `src/orchestrations/cli.py`; sequenced after O1 | C2, D1 |
| D1   | none (in wave 2) | sole owner of `README.md`, `src/CLI.md`, `cli.txt` | C2, O2 |
| V1   | all (format sweep) | `ruff format` may touch any file; run alone | none |

---

## 4d — Integration Workflow

Each agent works on a branch named `agent-<letter>-sprint<N>`. Integrate wave by wave.

```bash
# ---------- After Wave 1 completes (C1, O1, D2, P1) ----------
git checkout main
git merge agent-a-sprint1 --no-commit   # C1: src/config/base.py
git merge agent-b-sprint1 --no-commit   # O1: cli.py + orchestrations trim/deletes
git merge agent-c-sprint1 --no-commit   # D2: docs/configuration.md, .env.example
git merge agent-d-sprint1 --no-commit   # P1: pyproject.toml, ci.yml, uv.lock
# Disjoint files → expect no conflicts. If uv.lock differs, prefer P1's regenerated lock.
uv run pytest tests/ -m "not live"
uv lock --check
git commit -m "Merge Wave 1: C1, O1, D2, P1"

# ---------- After Wave 2 completes (C2, O2, D1) ----------
# Wave 2 agents branched from the post-Wave-1 main.
git checkout main
git merge agent-a-sprint2 --no-commit   # C2: configs/*.yaml, base.example.yaml
git merge agent-b-sprint2 --no-commit   # O2: lecture_pipeline.py + orchestrations/cli.py
git merge agent-c-sprint2 --no-commit   # D1: README.md, src/CLI.md, cli.txt
# O2 touched src/orchestrations/cli.py which O1 also changed in Wave 1 — because O2 branched
# from post-Wave-1 main, this merges cleanly. Resolve only if hand-edited concurrently.
uv run pytest tests/ -m "not live"
git commit -m "Merge Wave 2: C2, O2, D1"

# ---------- Wave 3 (V1) ----------
git checkout -b agent-a-sprint3
uv run ruff format src/ tests/
# add tests/test_cli_docs_consistency.py, fix any lint/format fallout
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run deptry src
uv run pytest tests/ -m "not live"
git checkout main && git merge agent-a-sprint3 --no-commit
git commit -m "Merge Wave 3: V1 verification + formatting + consistency tests"
```

> Non-destructive git only. Do not force-push or hard-reset shared branches. Push feature branches
> with `git push -u origin <branch>` and open PRs rather than pushing to `main` directly.

---

## 4e — Recommended Agent Assignments

### Two agents (~13h wall-clock)

| Agent | Wave 1 | Wave 2 | Wave 3 |
|-------|--------|--------|--------|
| **1** | O1 (2h) → P1 (3h) | O2 (3h) | V1 (3h) |
| **2** | C1 (2h) → D2 (2h) | C2 (3h) → D1 (3h) | — |

- Agent 1 takes the code/CI-critical path (O1 before O2; P1 in parallel).
- Agent 2 takes config + docs. Sync point after Wave 1 and Wave 2.
- Rough total: Wave 1 ≈ 5h (Agent 1 bound) + Wave 2 ≈ 6h (Agent 2 bound) + Wave 3 ≈ 3h ≈ **~14h**.

### Three agents (~9h wall-clock)

| Agent | Wave 1 | Wave 2 | Wave 3 |
|-------|--------|--------|--------|
| **1** | C1 (2h) | O2 (3h) | V1 (3h) |
| **2** | O1 (2h) | C2 (3h) | — |
| **3** | P1 (3h) → D2 (2h overlaps) | D1 (3h) | — |

- Agent 1 owns the load-bearing `raw` change, then the lecture-pipeline rewire, then verification.
- Agent 2 owns orchestrate wiring, then config split.
- Agent 3 owns CI/packaging + config docs, then docs/CLI alignment.
- Total ≈ Wave 1 (3h) + Wave 2 (3h) + Wave 3 (3h) ≈ **~9h**.

Suggested start: **sprint_1.md, Agent A (C1)** — it unblocks the most downstream work (C2 and O2).
