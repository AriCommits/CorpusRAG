# Plan 22: Kernel API, Simple MCP, First-Run Fixes

## Summary

CorpusRAG already has one collection namespace and shared generator sampling
(plan 21). What is still missing is a **small Python kernel** that ingest,
ask, and summarize go through — so MCP (the surface used “through you”) and
new utilities do not each reconstruct `RAGConfig` / `RAGAgent` /
`SummaryGenerator`. This plan adds that kernel, a four-tool `simple` MCP
profile, top-level `corpus ingest|ask|summarize` aliases, a light generator
cleanup onto `complete_prompt`, first-run wizard/doctor/port fixes that
blocked a 5-minute install demo, and deletion of the empty `vectorstores/`
husk.

End state: `from kernel import Corpus` can ingest, ask, and summarize
`--collection notes`. `corpus-mcp-server --profile simple` (and the new
default) exposes list / ingest / store_text / query / summarize. Nested
`corpus tools …` remains. Video, handwriting, lecture-pipeline, and TUI
are frozen except the wizard “Launch TUI Now” crash.

## Goals

- One `Corpus` kernel object: `ingest_path`, `ingest_text`, `ask`,
  `summarize`, `sample`, `complete`.
- MCP `simple` profile is the recommended “through me” tool list; it is
  the server default.
- Top-level CLI: `corpus ingest`, `corpus ask`, `corpus summarize`
  (nested tools stay as the full tree).
- Flashcard / quiz / summary generators call `tools.generation.complete_prompt`
  instead of each constructing an LLM backend.
- First-run path: persistent doctor works; HTTP Chroma port is 8001;
  wizard copy matches live CLI; Launch TUI Now does not crash; model
  name is editable; Compose Chroma healthcheck uses `/api/v2/heartbeat`.
- Empty `src/tools/rag/vectorstores/` package removed.
- Docs match the kernel, `simple` profile, and flattened commands.

## Non-Goals

- No plugin framework, setuptools entry points, or auto CLI↔MCP registry.
- No further adapter cleanup (`DatabaseBackend` ABC, `LLMBackend`,
  strategy subclasses / registry stay).
- No torch / sentence-transformers extra split.
- No rewrite of video, handwriting, lecture-pipeline, or TUI (except
  wiring Launch TUI Now to the real `RAGApp(agent, collection)` path).
- No change to `rag_` collection prefix or retrieval internals.
- No package rename to `corpusrag.*`.
- Historical `docs/plans/plan_1`–`plan_21` and `docs/phases/` left alone.

## Background / Context

Source: post-plan-21 branch `plan-21/sprint-1` and the simplification
advice: kernel first, not adapters; MCP as a short hand-picked list;
utilities = `sample` + `complete`; first-run mismatches that would stall
an install demo.

### Recorded decisions

- **R1 — Kernel location:** `src/kernel.py` (add to
  `pyproject.toml` `py-modules`). Class `Corpus`. Do not name it
  `corpus.py` (clashes with the Click group). Generators must **not**
  import `kernel` (avoid cycles: kernel → SummaryGenerator).
- **R2 — Kernel wraps existing types:** `ingest_*` → `RAGIngester` /
  `RAGAgent.ingest_text`; `ask` → `RAGAgent.query`; `summarize` →
  `SummaryGenerator.generate`; `sample` / `complete` →
  `tools.generation`. No new retrieval.
- **R3 — MCP default:** `VALID_PROFILES` gains `simple`.
  `register_simple_tools` = `list_collections`, `rag_ingest`,
  `store_text`, `rag_query`, `generate_summary`. Default
  `--profile` becomes `simple`. `dev` / `learn` / `full` unchanged
  in membership.
- **R4 — CLI:** add top-level aliases only. `corpus tools rag ingest`
  and `corpus tools rag query` should call the kernel so there is one
  implementation path. Do not delete nested groups.
- **R5 — Generators:** replace `create_backend` + `self.llm_backend.complete`
  with `complete_prompt(self.config, prompt)`. Keep Config classes and
  public `generate()` signatures.
- **R6 — First-run:** wizard HTTP `chroma_port` default **8001**; host
  screen also collects port; persistent `corpus doctor` uses
  `ChromaDBBackend` (no HTTP heartbeat); wizard finish text uses
  positional ingest and `query … -c`; Launch TUI Now constructs
  `RAGApp` like `tools.rag.cli.ui`; optional model Input after backend
  (default may stay the current Gemma id). Repo Compose Chroma
  healthcheck: `/api/v2/heartbeat`. Do not drop the MCP service from
  default compose.
- **R7 — Adapters:** delete only the empty `vectorstores/` package.
  Leave `DatabaseBackend`, LLM backends, strategy wrappers.

## Features / Tasks

### K1: Corpus kernel
**Files:** `src/kernel.py` (NEW), `pyproject.toml` (`py-modules`),
`tests/test_kernel.py` (NEW)
**Complexity:** M
**Depends on:** none

Add `Corpus.from_config_path(path) -> Corpus` and methods listed in R1–R2.
`from_config_path` loads YAML via `load_cli_db` / `RAGConfig`. Tests use
persistent Chroma tmp dirs and mock the LLM (`complete` / `query`) so they
stay off the `live` mark. Assert `ask` and `summarize` hit the same
`rag_<collection>` that `ingest_text` wrote. Do not change MCP or CLI in
this task.

### H1: Delete empty vectorstores package
**Files:** `src/tools/rag/vectorstores/` (DELETE),
`src/tools/rag/README.md` (drop the vectorstores line),
`tests/test_dead_code_removal.py`
**Complexity:** S
**Depends on:** none

Remove the husk. Extend dead-code tests so
`src/tools/rag/vectorstores/` does not exist. Do not touch
`DatabaseBackend` or strategies.

### F1: First-run wizard, doctor, Compose healthcheck
**Files:** `src/setup_wizard.py`, `src/tools/rag/doctor.py`,
`.docker/docker-compose.yml`,
`tests/unit/test_setup_wizard_config.py`,
`tests/unit/test_doctor.py` (NEW if none exists)
**Complexity:** M
**Depends on:** none

Implement R6. Wizard `save_config` writes the chosen port. Generated
compose (empty dir, HTTP mode) maps `{port}:8000` using that port
(already true; default must be 8001). Doctor: if
`config.database.mode == "persistent"`, list collections via
`ChromaDBBackend`; only HTTP mode probes
`/api/v2/heartbeat`. Launch TUI Now: load saved config after
`save_config` (order already saves first in `run_setup_wizard` — fix
the `RAGApp()` call to match `ui()`). Tests: default HTTP port 8001;
persistent doctor does not require a listener on host:port; Launch
helper constructs RAGApp with two args (unit-test the helper, do not
run Textual).

### G1: Generators use `complete_prompt`
**Files:** `src/tools/flashcards/generator.py`,
`src/tools/quizzes/generator.py`,
`src/tools/summaries/generator.py`,
`tests/unit/test_generation.py`, `tests/unit/test_tool_generators.py`
**Complexity:** M
**Depends on:** none

Drop per-generator `create_backend` / `self.llm_backend` for completion.
Keyword/outline extra LLM calls in summaries go through `complete_prompt`
too. Do not import `kernel`. Keep `generate()` return shapes.

### K2: Top-level ingest / ask / summarize CLI
**Files:** `src/cli.py`, `src/tools/rag/cli.py`, `cli.txt`,
`tests/unit/test_rag_cli.py`, `tests/test_cli_docs_consistency.py`
(only if examples need a new command; prefer updating `cli.txt` + README
in D1), `tests/unit/test_kernel_cli.py` (NEW)
**Complexity:** M
**Depends on:** K1

Add `corpus ingest PATH -c NAME`, `corpus ask QUERY -c NAME`,
`corpus summarize -c NAME` on the root group. Implementation constructs
`Corpus` and delegates. Point `tools.rag.cli` ingest and query at
`Corpus` as well. Refresh `cli.txt` so Property 1 still matches the live
tree (preserve encoding: the file may be UTF-16). Nested commands stay.

### K3: MCP `simple` profile + kernel call sites
**Files:** `src/mcp_server/profiles.py`, `src/mcp_server/server.py`,
`src/mcp_server/tools/dev.py`, `src/mcp_server/tools/learn.py`,
`tests/unit/test_mcp_profiles.py`, `tests/unit/test_mcp_server.py`,
`tests/unit/test_mcp_learn_tools.py`, `tests/unit/test_mcp_dev_tools.py`
**Complexity:** M
**Depends on:** K1

Add `simple` (R3). Default profile `simple`. `rag_query` / `rag_ingest` /
`store_text` / `generate_summary` go through `Corpus` (same config.raw
loading as today to build the kernel). Other learn/dev tools may keep
their current constructors. Tests: `simple` has exactly the five names
and not `generate_flashcards` / video tools; `full` still has both RAG
and learn; default `create_mcp_server` profile is `simple`.

### D1: Docs for kernel, simple MCP, flattened CLI, first-run
**Files:** `README.md`, `docs/architecture.md`,
`docs/mcp-integration.md`, `docs/tools-usage.md`,
`docs/troubleshooting.md`, `docs/docker-deployment.md`,
`src/CLI.md`, `src/mcp_server/README.md`
**Complexity:** M
**Depends on:** K2, K3, F1

Document the kernel as the Python extension point (`sample` +
`complete` for new utilities). Document `--profile simple` as the
recommended MCP face. Show top-level ingest/ask/summarize in Quick
Start. Doctor: persistent vs HTTP. HTTP Chroma host port 8001. Wizard
commands without `--path`. Do not scrape `docs/plans/`. Keep
`test_cli_docs_consistency` green (documented examples must resolve).

## New Dependencies

None.

## File Change Summary

| File | Task |
|------|------|
| `src/kernel.py` | K1 (new) |
| `pyproject.toml` | K1 (`py-modules`) |
| `tests/test_kernel.py` | K1 (new) |
| `src/tools/rag/vectorstores/` | H1 (delete) |
| `src/tools/rag/README.md` | H1 |
| `tests/test_dead_code_removal.py` | H1 |
| `src/setup_wizard.py` | F1 |
| `src/tools/rag/doctor.py` | F1 |
| `.docker/docker-compose.yml` | F1 |
| `tests/unit/test_setup_wizard_config.py` | F1 |
| `tests/unit/test_doctor.py` | F1 (new) |
| `src/tools/flashcards/generator.py` | G1 |
| `src/tools/quizzes/generator.py` | G1 |
| `src/tools/summaries/generator.py` | G1 |
| `tests/unit/test_generation.py` | G1 |
| `src/cli.py` | K2 |
| `src/tools/rag/cli.py` | K2 |
| `cli.txt` | K2 |
| `tests/unit/test_kernel_cli.py` | K2 (new) |
| `src/mcp_server/profiles.py` | K3 |
| `src/mcp_server/server.py` | K3 |
| `src/mcp_server/tools/dev.py` | K3 |
| `src/mcp_server/tools/learn.py` | K3 |
| `tests/unit/test_mcp_profiles.py` | K3 |
| `tests/unit/test_mcp_server.py` | K3 |
| `README.md` | D1 |
| `docs/architecture.md` | D1 |
| `docs/mcp-integration.md` | D1 |
| `docs/tools-usage.md` | D1 |
| `docs/troubleshooting.md` | D1 |
| `docs/docker-deployment.md` | D1 |
| `src/CLI.md` | D1 |
| `src/mcp_server/README.md` | D1 |

## Open Questions

None blocking. Default MCP profile changes to `simple` (R3); `full` remains
available for existing editor configs that pass `--profile full`.
