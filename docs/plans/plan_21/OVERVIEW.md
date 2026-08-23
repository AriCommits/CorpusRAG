# Plan 21: CorpusRAG Cleanup — Correctness, Dead Layers, Dedup, Docs

## Summary

CorpusRAG works as a RAG product but several public paths cannot run, tools
do not share a collection namespace, and the codebase carries unused
abstractions from earlier plugin designs. This plan unblocks the lecture
pipeline, study generators, handwriting ingest, and MCP transcribe; deletes
layers that nothing calls; collapses copy-pasted generators, retrieval
strategies, vision OCR, and MCP telemetry wrappers; then rewrites the
stale architecture docs to match the live `corpus` CLI.

End state: ingesting `--collection notes` and then generating flashcards,
summaries, or quizzes against `notes` hits the same Chroma collection
(`rag_notes`). `corpus orchestrate lecture-pipeline` transcribes without
`TypeError`. Handwriting ingest writes through `RAGAgent.ingest_text`.
MCP tools honor YAML `rag:`/`flashcards:`/`video:` via `config.raw`.
Retrieval is one staged strategy. Generators share one sampling/LLM
helper. Docs say CorpusRAG and the nested `corpus tools …` tree.

## Goals

- One user-facing collection name maps to one Chroma collection for RAG
  and all study generators (default prefix `rag_`).
- Lecture pipeline, MCP `transcribe_video`, summaries CLI, and handwriting
  ingest run against the real APIs (no `TypeError` / `AttributeError`).
- MCP constructs tool configs from `config.raw` (full merged YAML), not
  `to_dict()` (four modeled sections only).
- Unused LangChain vector adapter, RAG shims, dead TUI types, unused
  `SecretManager` / `tokens.py` / `db.models` removed; unused packages
  dropped from `pyproject.toml`.
- Generators share a sampling + LLM helper; hybrid/semantic/keyword share
  one staged retrieval implementation; video and handwriting share one
  vision-OCR client; MCP telemetry is one decorator.
- Parent documents are isolated per collection (BM25 no longer searches
  every parent JSON file).
- Architecture / tools / MCP / docker / troubleshooting docs match the
  live CLI and no longer say CorpusCallosum.

## Non-Goals

- No rename of the import layout to a `corpusrag.*` package.
- No unified CLI/MCP command registry (MCP stays a hand-written adapter;
  this plan only makes it call the same functions correctly).
- No split of torch out of the default extra (already documented in plan
  20 as infeasible while sentence-transformers is core).
- No new user-facing features: no handwriting `review` command, no
  `process_course` CLI, no video-OCR → Chroma path (lecture pipeline
  already indexes via `RAGIngester`).
- No change to embedding backends, Chroma schema, or Click as the CLI
  framework.
- No attempt to make the tree mypy-clean.

## Background / Context

Source: architecture audit of `main` at `5700d58` (plan 20 merged via PR
#7). Plan 20 fixed `BaseConfig.raw`, wired `orchestrate lecture-pipeline`,
split YAML, and aligned README/`src/CLI.md`/`cli.txt`. It did not fix
call-site bugs, collection prefixes, MCP `to_dict()` usage, or the
broader docs cluster.

### Recorded decisions

- **R1 — Collection namespace:** keep the `rag_` prefix. Change
  flashcards / quizzes / summaries defaults and `from_dict` fallbacks
  from `flashcards`/`quizzes`/`summaries` to `rag`. Existing
  `rag_<name>` collections keep working. Video `videos_` prefix is
  unused for Chroma and is left as-is (video OCR still writes markdown
  only).
- **R2 — `ingest_text`:** add `RAGAgent.ingest_text(text, collection,
  doc_id=None, metadata=None)` and `get_ingested_hashes(collection)`
  matching the handwriting caller. Implementation goes through
  `RAGIngester` (temp markdown + existing `ingest_path`, or a dedicated
  text path that still creates parent+child docs). Do not add a
  handwriting `review` command; point the CLI at the warnings file.
- **R3 — Lecture / MCP transcribe:** do not change
  `VideoTranscriber.__init__(config)` / `transcribe_file(path)`. Fix
  every call site that currently passes `db` or `collection`.
- **R4 — MCP config:** every `*Config.from_dict(...)` in
  `src/mcp_server/` uses `config.raw or config.to_dict()`. Pass
  `count`/`difficulty` into `generator.generate(...)`.
- **R5 — LangChain:** delete `LangChainVectorStoreAdapter`. Drop
  `langchain`, `langchain-community`, `langchain-chroma`. Keep
  `langchain-core` and `langchain-text-splitters` (Document + splitters).
  Keep `ChromaVectorStore` until S2; S2 may call `DatabaseBackend`
  directly and then delete the chroma adapter.
- **R6 — Strategies:** one staged implementation; registry names
  `hybrid` / `semantic` / `keyword` remain. Honor `reranking.enabled` /
  `reranking.model` / `retrieval.top_k_semantic` / `top_k_bm25` **or**
  delete those YAML knobs in the same task — no leftover dead config.
  Write `collection_name` on parent docs; store parents under
  `parent_store/<collection>/`; drop the
  `or not doc.metadata.get("collection_name")` BM25 clause.
- **R7 — Generators:** shared helper for “sample collection + call LLM +
  parse”. Stop padding quizzes/flashcards with fake Q&A. Drop the
  tiktoken `GENERATORS_AVAILABLE` gate unless the extra is actually
  imported. Fix summaries CLI to use the dict (`summary["summary"]`),
  not `.text`.
- **R8 — Docs:** rewrite in place (do not delete)
  `docs/architecture.md`, `docs/tools-usage.md`,
  `docs/mcp-integration.md`, `docs/docker-deployment.md`,
  `docs/troubleshooting.md`. Live command tree from `src/cli.py` is
  authoritative. Historical `docs/phases/` and `docs/plans/plan_1`–
  `plan_20` are left alone.
- **R9 — Packaging:** if `src/` no longer imports `keyring` /
  `cryptography` after deleting `utils/secrets.py`, drop those
  dependencies. Add any newly-unused packages to removal, not to
  `DEP002` ignores.

## Features / Tasks

### C1: Unify collection namespace + summaries CLI + stale command strings
**Files:** `src/tools/flashcards/config.py`, `src/tools/quizzes/config.py`,
`src/tools/summaries/config.py`, `src/tools/summaries/cli.py`,
`src/cli.py`, `src/setup_wizard.py`, `configs/base.example.yaml`,
`configs/generators.example.yaml`, `tests/unit/test_tools.py`,
`tests/integration/test_generators.py`
**Complexity:** M
**Depends on:** none

Change `collection_prefix` defaults and `from_dict` fallbacks on
flashcards / quizzes / summaries from their tool names to `"rag"`.
Integration fixtures already pass `collection_prefix="rag"`; assert the
dataclass default matches. In `summaries/cli.py`,
`generator.generate()` returns a dict — use `summary["summary"]` (and
`format_summary(summary)` which already accepts a dict), never
`.text`. Replace leftover `corpus rag …` strings in `src/cli.py` setup
message and `src/setup_wizard.py` with `corpus tools rag …`. Do **not**
edit generator bodies (S1 owns those).

### C2: Lecture pipeline uses the real VideoTranscriber API
**Files:** `src/orchestrations/lecture_pipeline.py`,
`tests/test_lecture_pipeline_config.py`,
`tests/unit/test_orchestrations.py`
**Complexity:** M
**Depends on:** none

`VideoTranscriber.__init__(self, config)` and `transcribe_file(self,
video_path: Path) -> str` are the API. Today the orchestrator calls
`VideoTranscriber(self.video_config, self.db)` and
`transcribe_file(video_path, collection_name)` — both `TypeError`.
Construct with config only; transcribe with the path only; keep using
`collection_name` for the temp markdown filename and `RAGIngester`.
Leave `process_course` as a library method (no new CLI). Do not edit
`src/tools/video/transcribe.py`. MCP transcribe is C5.

### C4: Implement `RAGAgent.ingest_text` for handwriting
**Files:** `src/tools/rag/agent.py`, `src/tools/rag/ingest.py`,
`src/tools/handwriting/cli.py`, `src/tools/rag/__init__.py` (if
exports needed), `tests/unit/` (new agent ingest tests),
`tests/tools/handwriting/test_ingest_handwriting.py` (keep FakeAgent;
add one test that a real `RAGAgent` exposes the methods)
**Complexity:** M
**Depends on:** none

Handwriting calls `agent.ingest_text(text=, collection=, doc_id=,
metadata=)` and optionally `agent.get_ingested_hashes(collection)`.
Neither exists on `RAGAgent`. Add both. `ingest_text` must create
searchable chunks in `rag_<collection>` (reuse `RAGIngester` —
temp file + `ingest_path` is acceptable if metadata/doc_id are
preserved on the resulting docs). `get_ingested_hashes` returns a
`set[str]` of already-ingested file hashes for that collection, or
empty if none. In `handwriting/cli.py`, replace the
``corpus handwriting review`` hint with a pointer at
`result.warnings_file`. Do not add a `review` command.

### C5: MCP uses `config.raw` and the real transcribe / generate APIs
**Files:** `src/mcp_server/tools/dev.py`, `src/mcp_server/tools/learn.py`,
`src/mcp_server/tools/video.py`, `src/mcp_server/profiles.py`,
`src/mcp_server/server.py`, `tests/unit/test_mcp_learn_tools.py`,
`tests/unit/test_mcp_dev_tools.py`, `tests/unit/test_mcp_video.py`,
`tests/unit/test_mcp_server.py`, `tests/test_mcp_tools.py`
**Complexity:** M
**Depends on:** none

Replace every `*Config.from_dict(config.to_dict())` in `mcp_server/`
with `from_dict(config.raw or config.to_dict())` so `rag:` /
`flashcards:` / `video:` YAML survive. Fix `transcribe_video` to
`VideoTranscriber(video_config)` + `transcribe_file(Path(video_path))`
(drop the unused `db`/`collection` constructor args). Pass
`count`/`difficulty` into `FlashcardGenerator.generate` and
`QuizGenerator.generate` instead of stuffing them into unused config
fields. `server.py` telemetry config should read
`(config.raw or config.to_dict()).get("telemetry", {})`. Do not
rewrite the `@mcp.tool()` telemetry wrappers (S4 owns `profiles.py`
structure after this); only change the `from_dict` line in
`register_video_tools` and any other config construction.

### D1: Delete unused RAG layers (LangChain adapter, shims, dead TUI types)
**Files:** `src/tools/rag/vectorstores/langchain_adapter.py` (DELETE),
`src/tools/rag/vectorstores/__init__.py`,
`src/tools/rag/embeddings.py` (DELETE),
`src/tools/rag/storage.py` (DELETE),
`src/tools/rag/markdown_parser.py` (DELETE),
`src/tools/rag/message.py` (DELETE),
`src/tools/rag/context.py` (DELETE),
`src/tools/flashcards/generator.py` (import path only),
`src/tools/quizzes/generator.py` (import path only),
`src/tools/summaries/generator.py` (import path only),
`tests/unit/test_rag_components.py`,
`tests/unit/test_message_metadata.py` (DELETE),
`tests/unit/test_tui_context.py` (DELETE),
`tests/test_strategies.py` (drop `vectorstore.backend` assertion if it
only existed for the unused knob — S2 owns knob removal from
`rag/config.py`; here only stop importing the adapter),
`tests/test_dead_code_removal.py`
**Complexity:** M
**Depends on:** none

Delete the unused LangChain adapter and the three 5-line shims
(`embeddings.py` / `storage.py` / `markdown_parser.py`). Point remaining
imports at `tools.rag.pipeline`. Delete `message.py` / `context.py` and
their unit tests (nothing in `src/` imports them; TUI uses session
`included` flags). Keep `ChromaVectorStore` and `vectorstores/base.py`
for S2. Do **not** edit `pyproject.toml` (D3 owns packaging). Do **not**
rewrite generator logic — import line only.

### D3: Delete unused utils and drop unused dependencies
**Files:** `src/utils/secrets.py` (DELETE), `src/utils/tokens.py` (DELETE),
`src/db/models.py` (DELETE), `src/db/__init__.py`,
`src/utils/__init__.py` (if it re-exports), `pyproject.toml`, `uv.lock`,
`tests/unit/test_tokens.py` (DELETE), `tests/test_dead_code_removal.py`,
`tests/test_security_storage.py` (only if it imported SecretManager)
**Complexity:** M
**Depends on:** none

`SecretManager` has no callers outside `secrets.py`. `utils.tokens` is
tests-only. `db.models.Document` / `QueryResult` have no production
imports (RAG uses LangChain `Document`). Delete the modules and tests
that exist only to cover them. Drop `keyring` and `cryptography` from
core deps if `src/` no longer imports them. Drop `langchain`,
`langchain-community`, `langchain-chroma` (R5); keep `langchain-core`
and `langchain-text-splitters`. Run `uv lock` after the edit. Prefer
removing a package over adding it to `DEP002`. Do not touch
`vectorstores/` (D1) or strategy code (S2).

### S3: Unify vision OCR client
**Files:** `src/tools/ocr_client.py` (NEW), `src/tools/video/ocr.py`,
`src/tools/handwriting/ocr.py`, `tests/unit/test_ocr.py`,
`tests/tools/handwriting/` (ocr tests if present)
**Complexity:** M
**Depends on:** none

Video OCR posts base64 to Ollama via `httpx`; handwriting uses the
`ollama` SDK. Extract one `ocr_image(image_path, prompt, *, model,
endpoint, timeout)` used by both. Keep the slide/chalkboard/handwriting
prompts in their current modules. Do not change ingest orchestration
(`ingest_handwriting.py` / `video/ingest.py`).

### S1: Collapse flashcards / quizzes / summaries onto a shared helper
**Files:** `src/tools/generation.py` (NEW),
`src/tools/flashcards/generator.py`, `src/tools/quizzes/generator.py`,
`src/tools/summaries/generator.py`, `src/tools/flashcards/config.py`,
`src/tools/quizzes/config.py`, `src/tools/summaries/config.py`,
`src/tools/flashcards/__init__.py`, `src/tools/quizzes/__init__.py`,
`src/tools/summaries/__init__.py`, `src/tools/summaries/cli.py` (only if
C1's dict fix must move), `tests/integration/test_generators.py`,
`tests/unit/test_tool_generators.py`, `tests/test_optional_extras.py`
**Complexity:** L
**Depends on:** C1, D1

Shared module: resolve `rag_<collection>`, sample documents via
`EmbeddingClient` + `db.query`, call `create_backend` +
`PromptTemplates`, return raw LLM text. Each generator keeps its parse /
export / format functions. Stop padding missing quiz/flashcard items
with placeholder Q&A; return what the model produced (or raise if
zero). Drop tiktoken `GENERATORS_AVAILABLE` stubs unless something in
`src/` actually imports tiktoken; if the extra becomes empty, leave the
optional extra in `pyproject.toml` for Anki/`genanki` via `export` —
do not invent a new extra. A small `from_dict` helper on `BaseConfig`
(copy llm/embedding/database/paths + section overlay) is in scope if it
lives in `src/config/base.py` **and** only this task edits that file.

### S2: One staged retrieval strategy + parent-store isolation
**Files:** `src/tools/rag/strategies/staged.py` (NEW),
`src/tools/rag/strategies/hybrid.py`, `src/tools/rag/strategies/semantic.py`,
`src/tools/rag/strategies/keyword.py`, `src/tools/rag/strategies/__init__.py`,
`src/tools/rag/strategies/base.py`, `src/tools/rag/retriever.py`,
`src/tools/rag/ingest.py`, `src/tools/rag/pipeline/storage.py`,
`src/tools/rag/config.py`, `src/tools/rag/vectorstores/chroma_adapter.py`
(DELETE if strategies call `db` directly),
`src/tools/rag/vectorstores/base.py` (DELETE if unused after adapter
removal), `src/tools/rag/vectorstores/__init__.py`,
`src/tools/rag/cli.py` (stop double-retrieve in `query`; drop no-op
`stream` branch if it lives here), `src/tools/rag/agent.py` (drop
`stream=True` no-op if still present after C4),
`configs/rag.example.yaml`, `configs/base.example.yaml` (`rag:` section
only), `tests/test_strategies.py`, `tests/unit/test_rag_components.py`
**Complexity:** L
**Depends on:** D1, C4

Replace copied `_vector_search` / `_keyword_search` / `_rerank` /
`_init_bm25` with one `StagedStrategy` configured by name (`hybrid`
runs vector+BM25+RRF+rerank; `semantic` vector+rerank; `keyword`
BM25). Keep registry names. Lazy-import CrossEncoder. Cache the
SentenceTransformer / CrossEncoder on the strategy. Either honor
`reranking.enabled` / `reranking.model` / `top_k_semantic` /
`top_k_bm25` or delete those fields from `RAGConfig` and example YAML
in this task.

Parent isolation: write `collection_name` (the unprefixed user name) on
every parent Document in `ingest.py`; store files under
`parent_store/<collection>/`; BM25 filter must be equality on
`collection_name` with **no** `or not collection_name` fallback.
Existing parent JSON without the field is ignored (no migration tool).

If `ChromaVectorStore` is still a pass-through, delete it and have
strategies take `DatabaseBackend`. CLI `query` currently calls
`agent.query` then `agent.retrieve` — retrieve once. `RAGAgent.query`
`stream=True` still calls `complete()`; delete the dead branch.

When editing `configs/base.example.yaml`, change only the `rag:`
section (C1 owns generator prefixes there).

### S4: One MCP telemetry decorator
**Files:** `src/mcp_server/profiles.py`,
`src/mcp_server/telemetry.py` (NEW) or a helper in
`src/mcp_server/middleware.py`, `tests/unit/test_mcp_profiles.py`,
`tests/unit/test_mcp_server.py`, `tests/unit/test_telemetry.py`
**Complexity:** M
**Depends on:** C5

`profiles.py` repeats `time.perf_counter()` / `store.log(...)` around
every tool (~15 copies). Replace with one decorator/wrapper that logs
name, duration, input size, success. Tool function bodies stay in
`tools/dev.py` / `learn.py` / `video.py`. Do not revert C5's
`config.raw` / transcribe signature fixes.

### DOC1: Rewrite stale architecture docs to the live CLI
**Files:** `docs/architecture.md`, `docs/tools-usage.md`,
`docs/mcp-integration.md`, `docs/docker-deployment.md`,
`docs/troubleshooting.md`, `docs/configuration.md` (collection-prefix
table and CorpusCallosum leftovers only)
**Complexity:** M
**Depends on:** C1, C2, C5, S1, S2, S4

Rewrite those six files so they describe CorpusRAG, the nested
`corpus tools rag|video|handwriting|summaries|learning …` tree,
`corpus orchestrate lecture-pipeline`, `corpus doctor`, and a **manual**
MCP subset (table of CLI command → MCP tool or “CLI-only”). Remove
`schema.py`, `study_session`, `knowledge_base`, `corpus-rag`,
`corpus-flashcards`, `collection://{name}`, `lecture_processing_prompt`,
and “auto-exposed MCP tools”. Collection table: one `rag_<name>`
namespace. Do not edit `docs/phases/` or `docs/plans/plan_*`. Do not
edit `src/cli.py` / `setup_wizard.py` (C1) or README/`src/CLI.md`
(already aligned in plan 20).

### V1: Verify, format, leftover bytecode, consistency tests
**Files:** any file `ruff format` rewrites; `tests/test_cli_docs_consistency.py`
(extend if docs claims are testable); `tests/test_dead_code_removal.py`;
`src/orchestrations/__pycache__/study_session*.pyc` and
`knowledge_base*.pyc` (delete if still on disk — they are gitignored)
**Complexity:** M
**Depends on:** DOC1, S1, S2, S4, D3

Single integration pass: `ruff format` + `ruff check` on `src/` and
`tests/`; `deptry src`; `pytest tests/ -m "not live"`. Confirm no
imports of deleted modules. Confirm lecture-pipeline, summaries CLI,
MCP transcribe, and generator prefix tests exist and pass. Extend
dead-code tests for the new deletes. Do not add features.

## New Dependencies

| Package | Feature | Optional? |
|---------|---------|-----------|
| *(none)* | This plan only removes packages | — |

Removals (D3): `langchain`, `langchain-community`, `langchain-chroma`;
`keyring` and `cryptography` if unused after deleting `secrets.py`.

## File Change Summary

| File | Action |
|------|--------|
| `src/tools/flashcards/config.py` | modify (C1, S1) |
| `src/tools/quizzes/config.py` | modify (C1, S1) |
| `src/tools/summaries/config.py` | modify (C1, S1) |
| `src/tools/summaries/cli.py` | modify (C1, S1 if needed) |
| `src/cli.py` | modify (C1) |
| `src/setup_wizard.py` | modify (C1) |
| `configs/base.example.yaml` | modify (C1 prefixes; S2 `rag:` knobs) |
| `configs/generators.example.yaml` | modify (C1) |
| `configs/rag.example.yaml` | modify (S2) |
| `src/orchestrations/lecture_pipeline.py` | modify (C2) |
| `src/tools/rag/agent.py` | modify (C4, S2 stream branch) |
| `src/tools/rag/ingest.py` | modify (C4, S2 parent metadata) |
| `src/tools/rag/__init__.py` | modify (C4 if exports) |
| `src/tools/handwriting/cli.py` | modify (C4) |
| `src/mcp_server/tools/dev.py` | modify (C5) |
| `src/mcp_server/tools/learn.py` | modify (C5) |
| `src/mcp_server/tools/video.py` | modify (C5) |
| `src/mcp_server/profiles.py` | modify (C5, S4) |
| `src/mcp_server/server.py` | modify (C5) |
| `src/mcp_server/telemetry.py` | new (S4) |
| `src/tools/rag/vectorstores/langchain_adapter.py` | delete (D1) |
| `src/tools/rag/vectorstores/__init__.py` | modify (D1, S2) |
| `src/tools/rag/vectorstores/chroma_adapter.py` | delete (S2, if unused) |
| `src/tools/rag/vectorstores/base.py` | delete (S2, if unused) |
| `src/tools/rag/embeddings.py` | delete (D1) |
| `src/tools/rag/storage.py` | delete (D1) |
| `src/tools/rag/markdown_parser.py` | delete (D1) |
| `src/tools/rag/message.py` | delete (D1) |
| `src/tools/rag/context.py` | delete (D1) |
| `src/tools/flashcards/generator.py` | modify (D1 import, S1 rewrite) |
| `src/tools/quizzes/generator.py` | modify (D1 import, S1 rewrite) |
| `src/tools/summaries/generator.py` | modify (D1 import, S1 rewrite) |
| `src/utils/secrets.py` | delete (D3) |
| `src/utils/tokens.py` | delete (D3) |
| `src/db/models.py` | delete (D3) |
| `src/db/__init__.py` | modify (D3) |
| `pyproject.toml` | modify (D3) |
| `uv.lock` | modify (D3) |
| `src/tools/ocr_client.py` | new (S3) |
| `src/tools/video/ocr.py` | modify (S3) |
| `src/tools/handwriting/ocr.py` | modify (S3) |
| `src/tools/generation.py` | new (S1) |
| `src/config/base.py` | modify (S1 helper, optional) |
| `src/tools/flashcards/__init__.py` | modify (S1) |
| `src/tools/quizzes/__init__.py` | modify (S1) |
| `src/tools/summaries/__init__.py` | modify (S1) |
| `src/tools/rag/strategies/staged.py` | new (S2) |
| `src/tools/rag/strategies/hybrid.py` | modify or thin-wrap (S2) |
| `src/tools/rag/strategies/semantic.py` | modify or thin-wrap (S2) |
| `src/tools/rag/strategies/keyword.py` | modify or thin-wrap (S2) |
| `src/tools/rag/strategies/__init__.py` | modify (S2) |
| `src/tools/rag/retriever.py` | modify (S2) |
| `src/tools/rag/pipeline/storage.py` | modify (S2) |
| `src/tools/rag/config.py` | modify (S2) |
| `src/tools/rag/cli.py` | modify (S2) |
| `docs/architecture.md` | modify (DOC1) |
| `docs/tools-usage.md` | modify (DOC1) |
| `docs/mcp-integration.md` | modify (DOC1) |
| `docs/docker-deployment.md` | modify (DOC1) |
| `docs/troubleshooting.md` | modify (DOC1) |
| `docs/configuration.md` | modify (DOC1) |
| `tests/unit/test_message_metadata.py` | delete (D1) |
| `tests/unit/test_tui_context.py` | delete (D1) |
| `tests/unit/test_tokens.py` | delete (D3) |
| various tests listed per task | modify |

## Open Questions

None blocking. If `keyring`/`cryptography` turn out to be imported from
a path missed in the audit, D3 keeps them and only deletes `secrets.py`
callers-none module after a repo-wide grep. If `ChromaVectorStore` is
still useful as a test seam, S2 may keep it — the requirement is that
strategies stop duplicating Chroma nested-list parsing, not that the
adapter file must die.
