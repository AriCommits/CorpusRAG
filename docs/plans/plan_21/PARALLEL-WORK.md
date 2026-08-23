# PARALLEL-WORK — Plan 21: CorpusRAG Cleanup

Coordination guide for executing `docs/plans/plan_21/`.
Source of truth: `OVERVIEW.md`. Per-agent briefs: `sprint_<N>.md`.

Tasks: **C1, C2, C4, C5, D1, D3, S3, S1, S2, S4, DOC1, V1**

---

## 4a — File Dependency Matrix

`██` = task modifies/creates/deletes this file.

```
                                         │ C1  C2  C4  C5  D1  D3  S3  S1  S2  S4  DOC V1
─────────────────────────────────────────┼──────────────────────────────────────────────
src/tools/flashcards/config.py           │ ██                      ██
src/tools/quizzes/config.py              │ ██                      ██
src/tools/summaries/config.py            │ ██                      ██
src/tools/summaries/cli.py               │ ██                      ██
src/cli.py                               │ ██
src/setup_wizard.py                      │ ██
configs/base.example.yaml                │ ██                          ██
configs/generators.example.yaml          │ ██
src/orchestrations/lecture_pipeline.py   │     ██
src/tools/rag/agent.py                   │         ██                  ██
src/tools/rag/ingest.py                  │         ██                  ██
src/tools/handwriting/cli.py             │         ██
src/mcp_server/tools/dev.py              │             ██
src/mcp_server/tools/learn.py            │             ██
src/mcp_server/tools/video.py            │             ██
src/mcp_server/profiles.py               │             ██                  ██
src/mcp_server/server.py                 │             ██
src/mcp_server/telemetry.py              │                                 ██
src/tools/rag/vectorstores/*             │                 ██          ██
src/tools/rag/{embeddings,storage,       │                 ██
              markdown_parser,message,   │
              context}.py                │
src/tools/*/generator.py (import)        │                 ██      ██
src/utils/secrets.py, tokens.py          │                     ██
src/db/models.py                         │                     ██
pyproject.toml, uv.lock                  │                     ██
src/tools/ocr_client.py                  │                         ██
src/tools/video/ocr.py                   │                         ██
src/tools/handwriting/ocr.py             │                         ██
src/tools/generation.py                  │                             ██
src/config/base.py                       │                             ██
src/tools/rag/strategies/*               │                                 ██
src/tools/rag/retriever.py               │                                 ██
src/tools/rag/config.py                  │                                 ██
src/tools/rag/cli.py                     │                                 ██
src/tools/rag/pipeline/storage.py        │                                 ██
configs/rag.example.yaml                 │                                 ██
docs/{architecture,tools-usage,          │                                     ██
      mcp-integration,docker-            │
      deployment,troubleshooting,        │
      configuration}.md                  │
ruff format sweep                        │                                         ██
```

Shared files across waves (must sequence, not parallelize):

| File | First owner | Later owner |
|------|-------------|-------------|
| generator configs / summaries CLI | C1 | S1 |
| `configs/base.example.yaml` | C1 (prefixes) | S2 (`rag:` only) |
| generator.py | D1 (import) | S1 (rewrite) |
| `agent.py`, `ingest.py` | C4 | S2 |
| `profiles.py` | C5 | S4 |
| `vectorstores/` | D1 | S2 |

---

## 4b — Wave Execution Plan

```
WAVE 1  (fully parallel — disjoint files)
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Agent A  │ │ Agent B  │ │ Agent C  │ │ Agent D  │
│ C1 ns +  │ │ C2 lect. │ │ C4 ingest│ │ C5 MCP   │
│ CLI/sum  │ │ pipeline │ │ _text    │ │ raw+API  │
│ ~2h  (M) │ │ ~2h  (M) │ │ ~3h  (M) │ │ ~2h  (M) │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Agent E  │ │ Agent F  │ │ Agent G  │
│ D1 dead  │ │ D3 utils │ │ S3 OCR   │
│ RAG layer│ │ + pkgs   │ │ client   │
│ ~2h  (M) │ │ ~2h  (M) │ │ ~3h  (M) │
└────┬─────┘ └────┬─────┘ └──────────┘
     │            │
     ▼            ▼
WAVE 2  (fully parallel — disjoint files; branched from post-Wave-1 main)
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Agent A  │ │ Agent B  │ │ Agent C  │
│ S1 gen.  │ │ S2 staged│ │ S4 MCP   │
│ helper   │ │ strategy │ │ decorator│
│ ~4h  (L) │ │ +parents │ │ ~2h  (M) │
│          │ │ ~4h  (L) │ │          │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     └────────────┼────────────┘
                  ▼
WAVE 3  (serial)
┌─────────────────────────────────────┐
│ Agent A: DOC1 — rewrite stale docs   │
│ ~3h  (M)                             │
└─────────────────┬───────────────────┘
                  ▼
WAVE 4  (serial)
┌─────────────────────────────────────┐
│ Agent A: V1 — format, deptry, pytest │
│ ~3h  (M)                             │
└─────────────────────────────────────┘
```

Critical path: **(C1 ‖ D1) → S1 → DOC1 → V1** and **(C4 ‖ D1) → S2 → DOC1 → V1**.
Wall-clock with enough agents ≈ Wave 1 (3h, bounded by C4/S3) + Wave 2 (4h) + Wave 3 (3h) + Wave 4 (3h) ≈ **~13h**.

---

## 4c — Conflict Table

| Task | Conflicts With | Reason | Safe to run with |
|------|----------------|--------|------------------|
| C1   | S1 (later), S2 (`base.example.yaml` later) | generator configs, summaries CLI, yaml prefixes | C2, C4, C5, D1, D3, S3 |
| C2   | none in-wave | sole owner of lecture_pipeline.py | all Wave 1 |
| C4   | S2 (later: agent.py, ingest.py) | handwriting ingest API | all Wave 1 |
| C5   | S4 (later: profiles.py) | MCP tool modules | all Wave 1 |
| D1   | S1 (later: generator imports), S2 (later: vectorstores) | shim/adapter deletes | all Wave 1 |
| D3   | none in-wave | sole owner of pyproject.toml / secrets / tokens / models | all Wave 1 |
| S3   | none | sole owner of OCR modules | all Wave 1 |
| S1   | C1, D1 (prior wave) | rewrites generators after prefix + import fix | S2, S4 |
| S2   | C4, D1 (prior wave) | strategies + parent isolation + adapter | S1, S4 |
| S4   | C5 (prior wave) | profiles.py wrappers | S1, S2 |
| DOC1 | none in-wave | docs only | — |
| V1   | all | format sweep | none |

---

## 4d — Integration Workflow

Each agent works on a branch named `agent-<letter>-sprint<N>`. Integrate wave by wave. Non-destructive git only — no force-push, no hard-reset of shared branches.

```bash
# ---------- After Wave 1 completes (C1, C2, C4, C5, D1, D3, S3) ----------
git checkout main
git merge agent-a-sprint1 --no-commit   # C1
git merge agent-b-sprint1 --no-commit   # C2
git merge agent-c-sprint1 --no-commit   # C4
git merge agent-d-sprint1 --no-commit   # C5
git merge agent-e-sprint1 --no-commit   # D1
git merge agent-f-sprint1 --no-commit   # D3
git merge agent-g-sprint1 --no-commit   # S3
# Disjoint files → expect no conflicts.
# If uv.lock and pyproject.toml only came from D3, keep D3's lock.
uv run pytest tests/ -m "not live"
uv lock --check
git commit -m "Merge Wave 1: C1 C2 C4 C5 D1 D3 S3"

# ---------- After Wave 2 completes (S1, S2, S4) ----------
# Wave 2 agents branched from post-Wave-1 main.
git checkout main
git merge agent-a-sprint2 --no-commit   # S1
git merge agent-b-sprint2 --no-commit   # S2
git merge agent-c-sprint2 --no-commit   # S4
# S2 may edit configs/base.example.yaml rag: section; C1 already changed prefixes.
# If both hunks land in the same file, keep both.
uv run pytest tests/ -m "not live"
git commit -m "Merge Wave 2: S1 S2 S4"

# ---------- Wave 3 (DOC1) ----------
git checkout -b agent-a-sprint3
# rewrite the six docs files per sprint_3.md
git checkout main && git merge agent-a-sprint3 --no-commit
git commit -m "Merge Wave 3: DOC1 docs rewrite"

# ---------- Wave 4 (V1) ----------
git checkout -b agent-a-sprint4
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run deptry src
uv run pytest tests/ -m "not live"
git checkout main && git merge agent-a-sprint4 --no-commit
git commit -m "Merge Wave 4: V1 verify + format"
```

Push feature branches with `git push -u origin <branch>` and open PRs rather than pushing to `main` directly.

---

## 4e — Recommended Agent Assignments

### Two agents (~18h wall-clock)

| Agent | Wave 1 | Wave 2 | Wave 3 | Wave 4 |
|-------|--------|--------|--------|--------|
| **1** | C4 (3h) → C2 (2h) → D1 (2h) | S2 (4h) | — | V1 (3h) |
| **2** | C1 (2h) → C5 (2h) → D3 (2h) → S3 (3h) | S1 (4h) → S4 (2h) | DOC1 (3h) | — |

- Agent 1 takes the RAG write/read path (C4 before S2; D1 before S2).
- Agent 2 takes generators + MCP + docs (C1 before S1; C5 before S4).
- Sync after Wave 1 and Wave 2.

### Three agents (~13h wall-clock)

| Agent | Wave 1 | Wave 2 | Wave 3 | Wave 4 |
|-------|--------|--------|--------|--------|
| **1** | C4 (3h) → D1 (2h) | S2 (4h) | — | V1 (3h) |
| **2** | C1 (2h) → C5 (2h) | S1 (4h) | DOC1 (3h) | — |
| **3** | C2 (2h) → D3 (2h) → S3 (3h) | S4 (2h) | — | — |

Suggested start: `sprint_1.md`, Agent A (C1) and Agent C (C4) first — they unblock S1 and S2.
