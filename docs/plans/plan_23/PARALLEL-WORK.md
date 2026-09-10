# PARALLEL-WORK — Plan 23: Fast CLI Help + Transcription Queue

Coordination guide for executing `docs/plans/plan_23/`.
Source of truth: `OVERVIEW.md`. Per-agent briefs: `sprint_1.md`, `sprint_2.md`.

Plan 23 is **one plan, two features**, shipped as two sprints:

| Sprint | Feature | Tasks |
|--------|---------|--------|
| 1 | Fast CLI help | A1, A2, A3, then A4 |
| 2 | Audio-only transcribe + boss-worker queue | B1, C1, B2, C2, B3, C3, C4, C5 |

They are not two plans. They only couple on `src/tools/video/cli.py` (Sprint 1 A2 moves imports; Sprint 2 C3 rewires `transcribe` / `pipeline`). Everything else in Sprint 2 can start on day one.

Tasks: **A1, A2, A3, A4, B1, B2, B3, C1, C2, C3, C4, C5**

---

## 4a — File Dependency Matrix

`██` = task modifies/creates/deletes this file.

```
                                         │ A1  A2  A3  A4  B1  B2  B3  C1  C2  C3  C4  C5
─────────────────────────────────────────┼──────────────────────────────────────────────
src/cli_lazy.py                          │ ██
src/cli.py                               │ ██
src/tools/cli.py                         │ ██
src/tools/learning/cli.py                │ ██
src/tools/rag/cli.py                     │     ██
src/tools/video/cli.py                   │     ██                          ██
src/tools/summaries/cli.py               │     ██
src/tools/flashcards/cli.py              │     ██
src/tools/quizzes/cli.py                 │     ██
src/tools/handwriting/cli.py             │     ██
src/db/management.py                     │     ██
src/db/collections_cli.py                │     ██
src/orchestrations/cli.py                │     ██
src/cli_common.py                        │         ██
src/db/__init__.py                       │         ██
tests/unit/test_cli_startup.py           │             ██
tests/unit/test_cli.py                   │             ██
src/tools/video/audio.py                 │                 ██
tests/unit/test_audio.py                 │                 ██
src/tools/video/transcribe.py            │                     ██      ██  ██
src/tools/video/config.py                │                     ██          ██
tests/unit/test_video_config.py          │                     ██
configs/base.yaml                        │                         ██
configs/base.example.yaml                │                         ██
configs/video.example.yaml               │                         ██
docs/configuration.md                    │                         ██              ██
src/tools/video/README.md                │                         ██              ██
src/tools/video/discover.py              │                             ██
tests/unit/test_discover.py              │                             ██
src/tools/video/pipeline_queue.py        │                                 ██
tests/unit/test_pipeline_queue.py        │                                 ██
src/tools/video/clean.py                 │                                 ██
tests/unit/test_video_cli.py             │                                     ██
src/orchestrations/lecture_pipeline.py   │                                         ██
tests/test_lecture_pipeline_config.py    │                                         ██
tests/unit/test_orchestrations.py        │                                         ██
src/CLI.md                               │                                             ██
docs/tools-usage.md                      │                                             ██
```

C2 may also touch `transcribe.py` / `clean.py` to inject `ModelGates` (after B2). C3 then touches `transcribe.py` again for folder combine — land C2 before C3.

---

## 4b — Wave Execution Plan

```
Feature 1: Fast CLI help                         Feature 2: Audio + queue
─────────────────────────                        ──────────────────────────
Sprint 1 Phase 1 (parallel)                      Sprint 2 Phase 1 (parallel, same day)
┌──────────┐  ┌──────────┐  ┌──────────┐         ┌──────────┐  ┌──────────┐
│ A1 lazy  │  │ A2 CLIs  │  │ A3 chroma│         │ B1 audio │  │ C1 disc. │
│  help    │  │  imports │  │  import  │         │  extract │  │          │
└────┬─────┘  └────┬─────┘  └────┬─────┘         └────┬─────┘  └────┬─────┘
     └─────────────┼─────────────┘                    │             │
                   ▼                                  ▼             │
Sprint 1 Phase 2                                 Sprint 2 Phase 2
┌──────────┐                                      ┌──────────┐
│ A4 help  │                                      │ B2 WAV   │
│  tests   │                                      │  whisper │
└──────────┘                                      └────┬─────┘
                                                       │
Feature 1 done.                                        ▼
                                                 Sprint 2 Phase 3 (parallel)
A2 ──────────────────────────────────────────►   ┌──────────┐  ┌──────────┐
   (only C3 waits on A2)                         │ C2 queue │  │ B3 audio │
                                                 │  mutex   │  │  docs    │
                                                 └────┬─────┘  └────┬─────┘
                                                      │             │
                                                 Sprint 2 Phase 4 (parallel)
                                                 ┌──────────┐  ┌──────────┐
                                                 │ C3 video │  │ C4 proc. │
                                                 │  CLI     │  │  course  │
                                                 └────┬─────┘  └────┬─────┘
                                                      └──────┬──────┘
                                                             ▼
                                                 Sprint 2 Phase 5
                                                 ┌──────────┐
                                                 │ C5 queue │
                                                 │  docs    │
                                                 └──────────┘
```

Estimated: Sprint 1 ~4.5h critical path (A2 2.5h + A4 2h). Sprint 2 ~12h critical path (B1 2 + B2 2 + C2 4 + C3 2.5 + C5 1.5). Wall clock with two people: ~12h (Feature 2 dominates; Feature 1 finishes on day one).

---

## 4c — Conflict Table

| Task | Conflicts With | Safe to run with |
|------|----------------|------------------|
| A1 | none | A2, A3, B1, C1, B2, C2, C4, B3 |
| A2 | **C3** (`video/cli.py`) | A1, A3, all of Feature 2 except C3 |
| A3 | none | A1, A2, entire Feature 2 |
| A4 | none (after A1–A3) | entire Feature 2 except it should see A1–A3 merged |
| B1 | none | A*, C1 |
| B2 | C2/C3 on `transcribe.py` (sequence: B2 → C2 → C3); C3 on `config.py` | A*, C1 |
| B3 | **C5** (`configuration.md`, `video/README.md`) | C2, C4 |
| C1 | none | A*, B1, B2 |
| C2 | C3 on `transcribe.py` (C2 first) | A*, B3, C1 (C1 must be done) |
| C3 | A2 (`video/cli.py`), B2/C2 (`transcribe.py`, `config.py`) | C4 |
| C4 | none once C2 exists | C3, B3 |
| C5 | B3 (same docs) — B3 first | none (last) |

---

## 4d — Integration Workflow

Base branch: `plan-23/dev` (off `plan-22/sprint-1`).

Single-agent (this repo’s usual pattern): stay on `plan-23/dev`, two feature commits (or one commit per phase).

```bash
git checkout plan-23/dev

# Feature 1
# A1, A2, A3 then A4
uv run pytest tests/ -m "not live"
git commit -m "plan_23 sprint 1: fast CLI help without importing heavy stacks"

# Feature 2 (can be started before Feature 1 finishes; merge A2 before C3)
uv run pytest tests/ -m "not live"
git commit -m "plan_23 sprint 2: audio-only transcribe and pipeline queue"
```

Split-agent workflow:

```bash
# After Sprint 1 Phase 1 (A1, A2, A3)
git checkout plan-23/dev
git merge agent-a-a1 --no-commit
git merge agent-b-a2 --no-commit
git merge agent-c-a3 --no-commit
uv run pytest tests/ -m "not live"
git commit -m "plan_23 sprint 1 phase 1: LazyGroup help and deferred CLI imports"

# A4 on the same branch
uv run pytest tests/unit/test_cli_startup.py tests/unit/test_cli.py tests/test_cli_docs_consistency.py
git commit -m "plan_23 sprint 1 phase 2: CLI help import-hygiene tests"

# Feature 2 may merge in parallel except C3
git merge agent-a-b1 --no-commit
git merge agent-b-c1 --no-commit
uv run pytest tests/unit/test_audio.py tests/unit/test_discover.py
git commit -m "plan_23 sprint 2 phase 1: extract_audio and discover_media_files"

# B2, then C2, then C3+C4, then C5
uv run pytest tests/ -m "not live"
```

Do not start C3 until A2 is on the branch. Rebase C3 onto `plan-23/dev` after the A2 merge; do not re-move imports that A2 already moved.

---

## 4e — Recommended Agent Assignments

### 2-agent team

| Agent | Sprint 1 | Sprint 2 |
|-------|----------|----------|
| A | A1 then A4 | B1 → B2 → C2 → C3 |
| B | A2 then A3 | C1 (with A's B1) → C4 (after C2) → B3 (after B2, before C5) → C5 |

A2 is on Agent B so Agent A is free to start B1 on day one. C3 waits until Agent B’s A2 is merged.

### 3-agent team

| Agent | Sprint 1 Phase 1 | Sprint 1 Phase 2 / Sprint 2 |
|-------|------------------|-----------------------------|
| A | A1 | A4, then B3, then C5 |
| B | A2 | C3 after C2 |
| C | A3 | B1 → B2 → C2; C1 can be Agent A after A1 (1h) or Agent C before B1 |

C4 (Agent B or C after C2) runs next to C3.

### 1-agent team

Sprint 1 (A1, A2, A3, A4) → Sprint 2 (B1, C1, B2, C2, B3, C4, C3, C5) on `plan-23/dev`. Prefer C4 before C3 if A2 just landed and you want a green lecture-pipeline test while finishing CLI flags.

Suggested start: `sprint_1.md`, Agent B (A2) if you only have one person about to touch video CLI; otherwise Agent A (A1) and Agent B (A2) together, and start `sprint_2.md` Agent A (B1) in parallel.
