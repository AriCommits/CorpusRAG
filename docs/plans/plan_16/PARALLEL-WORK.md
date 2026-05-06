# Parallel Work Coordination — Plan 16: Handwriting Ingestion

**Spec:** [handwriting_ingest_spec.md](handwriting_ingest_spec.md)
**Sprints:** [sprint_1.md](sprint_1.md) · [sprint_2.md](sprint_2.md) · [sprint_3.md](sprint_3.md) · [sprint_4.md](sprint_4.md)

---

## File Dependency Matrix

`██` = task creates/modifies the file. All `tools/handwriting/*.py` files are NEW; only `src/cli.py`, `pyproject.toml`, and `README.md` are modifications.

```
File                                        │ H1  H2  H3  H4  H5  H6  H7  H8
────────────────────────────────────────────┼──────────────────────────────
tools/handwriting/walker.py                 │ ██
tools/handwriting/preprocessor.py           │     ██
tools/handwriting/ocr.py                    │         ██
tools/handwriting/corrector.py              │             ██
tools/handwriting/postprocessor.py          │                 ██
tools/handwriting/chunker.py                │                 ██
tools/handwriting/ingest_handwriting.py     │                     ██
tools/handwriting/cli.py                    │                         ██
tools/handwriting/__init__.py               │                             ██
src/cli.py                       │                         ██
pyproject.toml                              │                             ██
README.md                                   │                             ██
tests/tools/handwriting/__init__.py         │                             ██
tests/tools/handwriting/test_walker.py      │ ██
tests/tools/handwriting/test_preprocessor.py│     ██
tests/tools/handwriting/test_ocr.py         │         ██
tests/tools/handwriting/test_corrector.py   │             ██
tests/tools/handwriting/test_postprocessor.py│                 ██
tests/tools/handwriting/test_chunker.py     │                 ██
tests/tools/handwriting/test_ingest_handwriting.py│                  ██
tests/tools/handwriting/test_cli.py         │                         ██
```

No two tasks modify the same file → no merge conflicts on file level.

---

## Wave Execution Plan

```
┌──────────────────────────── WAVE 1 (parallel × 5) ────────────────────────────┐
│                                                                                │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│ │ Agent A    │ │ Agent B    │ │ Agent C    │ │ Agent D    │ │ Agent E    │    │
│ │ H1 walker  │ │ H2 preproc │ │ H3 ocr     │ │ H4 correct │ │ H8 scaffold│    │
│ │ ~1.5 h     │ │ ~1.5 h     │ │ ~1.0 h     │ │ ~1.0 h     │ │ ~0.5 h     │    │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                                │
└─────────────────────────────────────┬──────────────────────────────────────────┘
                                      │  Merge wave 1 → main; run pytest
                                      ▼
┌──────────────────────────── WAVE 2 (single agent) ────────────────────────────┐
│ ┌─────────────────────────────────────────┐                                   │
│ │ Agent F: H5 postprocessor + chunker     │   needs: H1                       │
│ │ ~2.0 h                                  │                                   │
│ └─────────────────────────────────────────┘                                   │
└─────────────────────────────────────┬──────────────────────────────────────────┘
                                      │  Merge wave 2 → main; run pytest
                                      ▼
┌──────────────────────────── WAVE 3 (single agent) ────────────────────────────┐
│ ┌─────────────────────────────────────────┐                                   │
│ │ Agent G: H6 ingest_handwriting          │   needs: H1, H2, H3, H4, H5       │
│ │ ~3.0 h                                  │                                   │
│ └─────────────────────────────────────────┘                                   │
└─────────────────────────────────────┬──────────────────────────────────────────┘
                                      │  Merge wave 3 → main; run pytest
                                      ▼
┌──────────────────────────── WAVE 4 (single agent) ────────────────────────────┐
│ ┌─────────────────────────────────────────┐                                   │
│ │ Agent H: H7 cli + main cli wiring       │   needs: H6                       │
│ │ ~1.5 h                                  │                                   │
│ └─────────────────────────────────────────┘                                   │
└────────────────────────────────────────────────────────────────────────────────┘

Total wall-clock estimate (single dev):    ~12 h
Total wall-clock estimate (parallel):       ~8 h  (1.5 + 2 + 3 + 1.5)
```

---

## Conflict Table

| Task | Conflicts with | Safe to run with |
|------|----------------|------------------|
| H1   | none           | H2, H3, H4, H8   |
| H2   | none           | H1, H3, H4, H8   |
| H3   | none           | H1, H2, H4, H8   |
| H4   | none           | H1, H2, H3, H8   |
| H5   | none (file-wise); imports H1 | (must wait for H1 merge) |
| H6   | none (file-wise); imports H1–H5 | (must wait for H5 merge) |
| H7   | none (file-wise); imports H6 | (must wait for H6 merge) |
| H8   | none           | H1, H2, H3, H4   |

The dependencies are purely **import-chain** dependencies, not file-edit conflicts.

---

## Integration Workflow

Each wave should be merged before starting the next. Use a branch-per-task model.

```bash
# === WAVE 1 ===
# Each agent works on its own branch off main:
#   agent-a/h1-walker, agent-b/h2-preprocessor, agent-c/h3-ocr,
#   agent-d/h4-corrector, agent-e/h8-scaffolding
git checkout main
git pull
git merge --no-ff agent-a/h1-walker
git merge --no-ff agent-b/h2-preprocessor
git merge --no-ff agent-c/h3-ocr
git merge --no-ff agent-d/h4-corrector
git merge --no-ff agent-e/h8-scaffolding
pytest tests/tools/handwriting/ -v
git push

# === WAVE 2 ===
git checkout -b agent-f/h5-postprocessor-chunker
# ... agent F implements ...
git checkout main
git merge --no-ff agent-f/h5-postprocessor-chunker
pytest tests/tools/handwriting/ -v
git push

# === WAVE 3 ===
git checkout -b agent-g/h6-orchestrator
# ... agent G implements ...
git checkout main
git merge --no-ff agent-g/h6-orchestrator
pytest tests/tools/handwriting/ -v
git push

# === WAVE 4 ===
git checkout -b agent-h/h7-cli
# ... agent H implements ...
git checkout main
git merge --no-ff agent-h/h7-cli
pytest tests/ -v   # full suite — CLI touches main cli.py
corpus handwriting ingest --help    # smoke test
git push
```

No conflict-resolution should be needed since no two tasks share a file. If a merge does conflict, it indicates either:
1. Wave ordering was violated, or
2. Sprint scope leaked outside the file list — investigate before forcing the merge.

---

## Recommended Agent Assignments

### 2-agent schedule

| Wave | Agent 1                              | Agent 2                            |
|------|--------------------------------------|------------------------------------|
| 1    | H1 walker → H3 ocr (~2.5 h)          | H2 preproc → H4 correct → H8 (~3 h)|
| 2    | H5 postprocessor + chunker (~2 h)    | (idle / start writing H6 tests)    |
| 3    | H6 orchestrator (~3 h)               | (review H6 / start H7 stub)        |
| 4    | H7 CLI + wire-up (~1.5 h)            | (review)                           |

**Total wall-clock: ~9 h.** Critical path: H1 → H5 → H6 → H7.

### 3-agent schedule

| Wave | Agent 1                  | Agent 2                  | Agent 3            |
|------|--------------------------|--------------------------|--------------------|
| 1    | H1 walker (~1.5 h)       | H2 preproc + H4 (~2.5 h) | H3 ocr + H8 (~1.5 h)|
| 2    | H5 (~2 h)                | (review H1/H2/H3/H4)     | (review)           |
| 3    | H6 (~3 h)                | (review H5; pair on H6)  | (write H7 tests)   |
| 4    | H7 (~1.5 h)              | (review)                 | (final QA)         |

**Total wall-clock: ~8 h.** Diminishing returns past 3 agents — Waves 2, 3, 4 are inherently serial.

---

## Suggested Starting Point

Kick off **all five Wave 1 agents simultaneously** — they share no files and no imports. Once they merge cleanly, the rest of the plan is a serial chain (H5 → H6 → H7) where parallelism cannot help further.

Critical path for the project: **H1 → H5 → H6 → H7** (≈ 8 h of serial work). Anything optimizing this path (e.g., merging H5 sooner) speeds up the whole plan; anything else is slack.
