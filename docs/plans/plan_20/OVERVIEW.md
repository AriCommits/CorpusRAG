# Plan 20: CorpusRAG Portfolio Hardening

## Summary

CorpusRAG is functionally rich but not yet portfolio-quality. An audit found documentation
drifted from the actual CLI, configuration examples that reference invalid values and outdated
schemas, one orphaned command, contradictory dependency groups, docs that assume RAG expertise,
and a CI pipeline at risk of failing. This plan hardens the repository into a clean, internally
consistent, green-CI project.

Two changes are load-bearing and most other work depends on them:

1. **Full merged-config propagation.** `BaseConfig.to_dict()` emits only the four sections it
   models (`llm`, `embedding`, `database`, `paths`). Orchestrators build their sub-tool configs
   from `config.to_dict()`, so `video`, `rag`, `summaries`, `flashcards`, `quizzes`, and
   `orchestrations` settings are silently dropped. This is the root cause of the lecture-pipeline
   plumbing bug and must be fixed by carrying the full merged dict on the `BaseConfig` instance.
2. **CLI/documentation single source of truth.** The documented command tree has drifted from the
   Click command tree in `src/cli.py`. The live command tree is authoritative; docs and
   consistency checks derive from it.

> **Note:** This plan directory (`docs/plans/plan_20/`) is the source of truth for this effort, at
> the user's request. It supersedes the earlier `.kiro/specs/project-hardening/` requirements and
> design drafts, whose content has been consolidated here.

## Goals

- Documentation matches the actual CLI (`corpus tools rag ...` nested form, `doctor` present,
  `orchestrate lecture-pipeline` documented).
- Rebrand every user-facing reference from "CorpusCallosum"/"Corpus Callosum" to "CorpusRAG".
- Resolve the orphaned `orchestrate` command: wire it in scoped to `lecture-pipeline`; remove the
  `study-session` command and the `KnowledgeBaseOrchestrator` dead code.
- Make the lecture pipeline configuration-driven so it runs with minimal per-invocation flags.
- Correct configuration examples/docs to match what the code accepts; split config into scoped
  per-tool files while keeping a fully-commented reference.
- Add a plain-language newcomer primer without removing technical depth.
- Make CI reliably green on GitHub-hosted runners (CPU torch on Linux, synced lock, formatted code,
  deptry, drop unused mypy config).
- Remove dependency/packaging contradictions (duplicate `ruff` pin, false "slim server" claim).

## Non-Goals

- No new user-facing features beyond fixing/wiring the existing lecture pipeline.
- No change to the RAG retrieval algorithm, embedding backends, or database schema.
- No attempt to make the codebase pass strict `mypy` (explicitly deferred; config removed).
- No migration away from ChromaDB or Click.

## Background / Context

- **CLI:** `src/cli.py` is a Click `LazyGroup` with `lazy_subcommands={tools, db, collections, dev}`
  plus commands `setup`/`benchmark`/`doctor`. `src/tools/cli.py` nests
  `rag/video/handwriting/summaries/learning`. `orchestrate` (`src/orchestrations/cli.py`) is not
  registered anywhere and has no entry point.
- **Config:** `config/loader.py` supports base + tool-specific deep merge via
  `load_config(config_path, base_path)` and `CC_`-prefixed env overrides. `BaseConfig`
  (`config/base.py`) models only `llm/embedding/database/paths`; `to_dict()` emits only those four.
- **LLM backends:** `LLMBackendType` accepts only `ollama`/`openai_compatible`/`anthropic_compatible`.
  `base.example.yaml` wrongly documents `openai`/`anthropic`.
- **CI:** `.github/workflows/ci.yml` runs lint (ruff), a test matrix (3.11/3.12), and a docker build.
  It forces CUDA torch (`pytorch-cu128`) on Linux, sets a dead `CORPUSRAG_CONFIG` env, and never runs
  the configured `mypy`/`deptry`.

### Recorded decisions

- **D1 — Orchestrate scope:** wire in `orchestrate` exposing only `lecture-pipeline`; remove
  `study-session`, `StudySessionOrchestrator`, and `KnowledgeBaseOrchestrator`; keep
  `LecturePipelineOrchestrator`.
- **D2 — Config propagation:** carry the full merged dict as a non-comparable `BaseConfig.raw` field
  populated in `from_dict`; build sub-tool configs from `raw`. `to_dict()` unchanged (still masks
  secrets).
- **D3 — CPU torch in CI:** conditional `uv` sources — CPU index for Linux, CUDA index for Windows.
- **D4 — mypy/deptry:** run `deptry` in the lint job; remove the `[tool.mypy]` config rather than
  gate CI on a type-clean pass the codebase does not achieve.
- **D5 — server slim group:** a torch-free `server` install is not feasible (sentence-transformers
  needs torch); correct the docs to state the real footprint instead of claiming a slim path.

## Features / Tasks

### C1: Config loader full-dict propagation
**Files:**
- `src/config/base.py` — add `raw: dict = field(default_factory=dict, compare=False, repr=False)`;
  populate `raw = data` in `BaseConfig.from_dict`. Leave `to_dict()` unchanged.
- `tests/test_config_raw_propagation.py` (NEW) — unit + Hypothesis tests for `raw` population and
  deep-merge semantics.

**Complexity:** M
**Depends on:** none

Carry the untyped merged document on the typed config so downstream `*.from_dict()` calls see all
sections. Add a property test for `deep_merge` (retention, override-wins, recursive merge) and a unit
test that `from_dict(data).raw == data`.

### C2: Configuration restructuring + example correctness
**Files:**
- `configs/base.yaml` (NEW) — core: exactly `llm`, `embedding`, `database`, `paths`.
- `configs/rag.yaml` (NEW) — `rag:` section only.
- `configs/video.yaml` (NEW) — `video:` section only.
- `configs/generators.yaml` (NEW) — `summaries:`/`flashcards:`/`quizzes:` sections.
- `configs/orchestrations.yaml` (NEW) — `orchestrations:` section (incl. `lecture_pipeline`).
- `configs/base.example.yaml` — remains the fully-commented Reference_Config (all sections);
  fix invalid backend values (`openai`→`openai_compatible`, `anthropic`→`anthropic_compatible`),
  rebrand CorpusCallosum→CorpusRAG, and switch command examples to `corpus tools rag ...`.
- `tests/test_config_split_merge.py` (NEW) — Hypothesis split/merge equivalence + base-only load +
  missing/garbage tool file behavior + `load_config(base.example.yaml)` loads clean.

**Complexity:** M
**Depends on:** C1

Split the monolith into scoped files; deep-merge each onto `base.yaml`. Preserve backward
compatibility (single base file still loads). The Reference_Config keeps documenting every option.

### O1: Orchestrate CLI wiring + dead-code removal
**Files:**
- `src/cli.py` — add `"orchestrate": "orchestrations.cli:orchestrate"` to root `lazy_subcommands`.
- `src/orchestrations/cli.py` — remove the `study_session` command; keep only `lecture_pipeline`;
  rebrand docstring to CorpusRAG.
- `src/orchestrations/study_session.py` (DELETE) — `StudySessionOrchestrator`.
- `src/orchestrations/knowledge_base.py` (DELETE) — `KnowledgeBaseOrchestrator`.
- `src/orchestrations/__init__.py` — trim `__all__` and lazy `__getattr__` to
  `LecturePipelineOrchestrator` only.
- `tests/test_orchestrate_cli.py` (NEW) — `CliRunner` resolves `corpus orchestrate lecture-pipeline
  --help`; `orchestrate.list_commands() == ["lecture-pipeline"]`; removed modules no longer import.

**Complexity:** M
**Depends on:** none

### O2: Lecture-pipeline config wiring + counts + config-driven defaults
**Files:**
- `src/orchestrations/lecture_pipeline.py` — build `VideoConfig/RAGConfig/SummaryConfig/
  FlashcardConfig/QuizConfig` from `config.raw`; read `orchestrations.lecture_pipeline` defaults;
  pass configured counts via the generators' `count` parameter and use configured `summary_length`.
- `src/orchestrations/cli.py` — make `lecture-pipeline` require only essential inputs (video path,
  `--course`, `--lecture`); all other options default from config; supplied flags override config.
- `tests/test_lecture_pipeline_config.py` (NEW) — Hypothesis tests for full-dict propagation,
  count/length application, and flag-overrides-config precedence (tools/db mocked).

**Complexity:** M
**Depends on:** C1, O1 (shares `src/orchestrations/cli.py`)

### D1: Documentation-CLI alignment + newcomer primer
**Files:**
- `README.md` — use `corpus tools rag ...` throughout; add a plain-language primer (RAG, embedding,
  vector, collection, chunking, BM25, reranking, MCP, Ollama, ChromaDB) ahead of the first technical
  instruction; document `orchestrate lecture-pipeline`; rebrand.
- `src/CLI.md` — align the command tree to `src/cli.py`; add `orchestrate lecture-pipeline`; rebrand.
- `cli.txt` — regenerate to match `corpus --help` exactly (includes `doctor`, `tools`,
  `orchestrate`); fix the mojibake em dash and "Corpus Callosum" in the header.

**Complexity:** L
**Depends on:** O1 (cli.txt/CLI.md must reflect the registered `orchestrate` command)

### D2: Configuration docs rewrite + env cleanup
**Files:**
- `docs/configuration.md` — update field names to the current schema (`child_chunk_size`,
  `summary_length`, `whisper_model`, actual generator field names); remove non-existent commands
  (`corpus-config`, `corpus-secrets`); remove the `corpus_callosum.config.base` import; keep only
  real entry points (`corpus`, `corpus-mcp-server`); document `CC_` prefix; rebrand.
- `configs/.env.example` — rebrand header to CorpusRAG.

**Complexity:** M
**Depends on:** none

### P1: CI reliability + dependency/packaging cleanup
**Files:**
- `pyproject.toml` — remove the duplicate `ruff` pin (keep in `dev` only); add a `pytorch-cpu` index
  and make `torch/torchvision/torchaudio` sources conditional (CPU on Linux, CUDA on Windows); remove
  `[tool.mypy]` and its overrides; correct the `server` group's documented footprint.
- `.github/workflows/ci.yml` — remove the dead `CORPUSRAG_CONFIG` env; add a `deptry` step to the
  lint job.
- `uv.lock` — regenerate so `uv lock --check` passes with the new sources.

**Complexity:** L
**Depends on:** none

### V1: Verification, formatting, and consistency tests
**Files:**
- `tests/test_cli_docs_consistency.py` (NEW) — walk the live Click tree; assert `cli.txt` equals the
  reachable command set and that every `README.md`/`src/CLI.md` command example resolves.
- Repo-wide `ruff format` sweep so `ruff format --check` reports zero diffs.

**Complexity:** M
**Depends on:** C1, C2, O1, O2, D1, D2, P1

## New Dependencies

None added. `deptry` and `ruff` already exist in the `dev` extra; a `pytorch-cpu` uv index is added
(no new PyPI package).

## File Change Summary

| File | Task(s) | Action |
|------|---------|--------|
| `src/config/base.py` | C1 | modify |
| `configs/base.yaml` | C2 | new |
| `configs/rag.yaml` | C2 | new |
| `configs/video.yaml` | C2 | new |
| `configs/generators.yaml` | C2 | new |
| `configs/orchestrations.yaml` | C2 | new |
| `configs/base.example.yaml` | C2 | modify |
| `src/cli.py` | O1 | modify |
| `src/orchestrations/cli.py` | O1, O2 | modify |
| `src/orchestrations/study_session.py` | O1 | delete |
| `src/orchestrations/knowledge_base.py` | O1 | delete |
| `src/orchestrations/__init__.py` | O1 | modify |
| `src/orchestrations/lecture_pipeline.py` | O2 | modify |
| `README.md` | D1 | modify |
| `src/CLI.md` | D1 | modify |
| `cli.txt` | D1 | modify |
| `docs/configuration.md` | D2 | modify |
| `configs/.env.example` | D2 | modify |
| `pyproject.toml` | P1 | modify |
| `.github/workflows/ci.yml` | P1 | modify |
| `uv.lock` | P1 | regenerate |
| `tests/test_config_raw_propagation.py` | C1 | new |
| `tests/test_config_split_merge.py` | C2 | new |
| `tests/test_orchestrate_cli.py` | O1 | new |
| `tests/test_lecture_pipeline_config.py` | O2 | new |
| `tests/test_cli_docs_consistency.py` | V1 | new |

## Open Questions

- **Q1:** Should the deleted `.kiro/specs/project-hardening/` drafts be removed now that this plan is
  the source of truth? (Pending user confirmation — deletion is destructive.)
- **Q2:** `configs/base.example.yaml` is edited by C2 (correctness/rebrand) and is the single
  Reference_Config. If a future task also touches it, sequence after C2 to avoid conflict.
- **Q3:** The `count` wiring assumes the flashcard/quiz generators accept a `count` parameter on
  `generate(...)`; O2 must verify the actual generator signatures before relying on it.
