# Sprint 2 — Build-Out (Config Split, Lecture Pipeline, Docs/CLI Alignment)

**Plan:** docs/plans/plan_20/OVERVIEW.md
**Wave:** 2 of 3
**Can run in parallel with:** all agents in this wave (C2, O2, D1 touch disjoint files)
**Must complete before:** Sprint 3 (V1 depends on everything)
**Prerequisites:** Sprint 1 merged — C1 (`BaseConfig.raw`) and O1 (`orchestrate` registered,
`src/orchestrations/cli.py` trimmed) must be complete.

---

## Agents in This Wave

### Agent A: C2 — Configuration restructuring + example correctness

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `configs/base.yaml` (NEW) — exactly `llm`, `embedding`, `database`, `paths`.
- `configs/rag.yaml` (NEW) — `rag:` only.
- `configs/video.yaml` (NEW) — `video:` only.
- `configs/generators.yaml` (NEW) — `summaries:`/`flashcards:`/`quizzes:`.
- `configs/orchestrations.yaml` (NEW) — `orchestrations:` (incl. `lecture_pipeline`).
- `configs/base.example.yaml` — remains the fully-commented Reference_Config; fix backend values,
  rebrand, and switch command examples to `corpus tools rag ...`.
- `tests/test_config_split_merge.py` (NEW)

**Depends on:** C1 (uses `BaseConfig.raw` for equivalence assertions)
**Blocks:** none directly (V1 validates)

**Instructions:**
Carve the existing monolith into scoped files. `configs/base.yaml` holds only the four `BaseConfig`
sections. Each scoped file contains only its own top-level section(s) and is intended to be loaded as
`load_config("configs/<tool>.yaml", "configs/base.yaml")`. Keep `configs/base.example.yaml` as the
single fully-commented reference documenting every option (do not delete comments).

In `base.example.yaml`, correct invalid LLM backend values (`openai`→`openai_compatible`,
`anthropic`→`anthropic_compatible`), rebrand "CorpusCallosum"→"CorpusRAG", and convert flat
`corpus rag ...` command examples to `corpus tools rag ...`.

Tests (Hypothesis where noted, ≥100 iterations, tagged with the property comment):
- `# Feature: project-hardening, Property 4: split-then-merge preserves resolved configuration` —
  generate a combined doc, split into base (4 sections) + tool file (rest), and assert
  `load_config(tool, base)` resolves each tool's config identically to `Config.from_dict(combined)`
  (compare via `.raw` and typed fields).
- Unit: `base.yaml` top-level keys == `{llm, embedding, database, paths}`; each scoped file contains
  only its section(s); `load_config("configs/base.example.yaml", "configs/base.example.yaml")`
  loads without error; base-only load succeeds; a missing/garbage tool file raises identifying the
  path with no partial merge applied.

**Definition of Done:**
- [ ] Scoped files created; core `base.yaml` limited to the four sections.
- [ ] Reference `base.example.yaml` corrected (backends, rebrand, command form) and still complete.
- [ ] Split/merge equivalence property test passes ≥100 iterations.
- [ ] Copied example config loads without error; base-only + error paths covered.
- [ ] No regressions.

---

### Agent B: O2 — Lecture-pipeline config wiring + counts + config-driven defaults

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/orchestrations/lecture_pipeline.py`
- `src/orchestrations/cli.py` (the `lecture_pipeline` command)
- `tests/test_lecture_pipeline_config.py` (NEW)

**Depends on:** C1 (`BaseConfig.raw`), O1 (registered group + trimmed `cli.py`)
**Blocks:** none (V1 validates)

**Instructions:**
In `LecturePipelineOrchestrator.__init__`, build sub-tool configs from the full merged document:
```python
merged = config.raw or config.to_dict()   # full document; safe fallback
self.video_config     = VideoConfig.from_dict(merged)
self.rag_config       = RAGConfig.from_dict(merged)
self.summary_config   = SummaryConfig.from_dict(merged)
self.flashcard_config = FlashcardConfig.from_dict(merged)
self.quiz_config      = QuizConfig.from_dict(merged)
self.pipeline_opts    = (merged.get("orchestrations", {}) or {}).get("lecture_pipeline", {})
```
**First verify the generator signatures** (Open Question Q3): confirm `FlashcardGenerator.generate`
and `QuizGenerator.generate` accept a `count` parameter. Pass configured counts through that `count`
parameter; do not mutate the stale `cards_per_topic`/`questions_per_topic` attributes the way the
removed `StudySessionOrchestrator` did. Use the configured `summary_length` via `SummaryConfig`.

In the `lecture_pipeline` CLI command (`src/orchestrations/cli.py`): make only the essential inputs
required — the `video_path` argument, `--course`, and `--lecture`. Every other option
(`--skip-clean`, counts, summary length, etc.) must default to `None`/sentinel and fall back to the
configured value when not supplied; when supplied, the flag overrides config for that run.

> **Merge note:** O1 also edited `src/orchestrations/cli.py` in Wave 1. Rebase onto the merged Wave-1
> result before editing; your changes are confined to the `lecture_pipeline` command body/options.

Tests (Hypothesis, ≥100 iterations, tagged):
- `# ... Property 5: full merged configuration propagates to all sub-tool configs` — populated tool
  sections in `raw` ⇒ each sub-tool config field equals the configured value (mock `DatabaseBackend`).
- `# ... Property 6: configured counts and summary length are applied by the pipeline` — spy on
  `generate(count=...)` and summary length usage.
- `# ... Property 7: a supplied flag overrides the configured value` — via `CliRunner`, tools mocked.

**Definition of Done:**
- [ ] Sub-tool configs built from `config.raw`; configured values applied (not defaults).
- [ ] Counts routed via generator `count` param; `summary_length` honored; no stale-attr mutation.
- [ ] `lecture-pipeline` requires only video path + `--course` + `--lecture`; flags override config.
- [ ] Properties 5, 6, 7 pass ≥100 iterations; missing-essential-input yields a usage error.
- [ ] No regressions.

---

### Agent C: D1 — Documentation-CLI alignment + newcomer primer

**Complexity:** L
**Estimated time:** 3 hours
**Files to modify:**
- `README.md`
- `src/CLI.md`
- `cli.txt`

**Depends on:** O1 (docs must reflect the now-registered `orchestrate lecture-pipeline`)
**Blocks:** none (V1 validates)

**Instructions:**
Align all three to the live command tree in `src/cli.py`:
- Use the nested `corpus tools rag ...` form everywhere; remove flat `corpus rag ...` except inside a
  clearly headed "Migration note" section if you keep one.
- Add `corpus orchestrate lecture-pipeline` to the command tree in `README.md` and `src/CLI.md`, with
  a short usage example showing it needs only the video path, `--course`, and `--lecture`.
- Regenerate `cli.txt` so it matches `corpus --help` exactly: top-level commands include `benchmark`,
  `collections`, `db`, `dev`, `doctor`, `orchestrate`, `setup`, `tools`. Fix the mojibake em dash and
  replace "Corpus Callosum" in the header with "CorpusRAG".
- Add a plain-language primer to `README.md` **ahead of the first technical instruction** (before
  Quick Start), defining in everyday language: RAG, embedding, vector, collection, chunking, BM25,
  reranking, MCP, Ollama, ChromaDB. Do not remove or shrink any existing technical section.

Do not edit `docs/configuration.md`/`.env.example` (D2) or `configs/base.example.yaml` (C2).

**Definition of Done:**
- [ ] `cli.txt` matches `corpus --help` exactly (incl. `doctor`, `tools`, `orchestrate`); header
      rebranded; mojibake fixed.
- [ ] README + CLI.md use `corpus tools rag ...`; `orchestrate lecture-pipeline` documented.
- [ ] Newcomer primer defines all ten concepts before the first technical instruction.
- [ ] No existing technical section removed; rebrand complete in these files.
- [ ] No regressions.
