# Sprint 1 — Correctness and Dead-Layer Removal

**Plan:** docs/plans/plan_21/OVERVIEW.md
**Wave:** 1 of 4
**Can run in parallel with:** all agents in this wave (C1, C2, C4, C5, D1, D3, S3 touch disjoint files)
**Must complete before:** Sprint 2 (C1+D1 unblock S1; C4+D1 unblock S2; C5 unblocks S4)

---

## Agents in This Wave

### Agent A: C1 — Unify collection namespace + summaries CLI + stale command strings

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/flashcards/config.py` — default and `from_dict` fallback `collection_prefix` → `"rag"`.
- `src/tools/quizzes/config.py` — same.
- `src/tools/summaries/config.py` — same.
- `src/tools/summaries/cli.py` — `generate()` returns a dict; use `summary["summary"]`, not `.text`.
- `src/cli.py` — setup already-complete message: `corpus tools rag ui`, not `corpus rag ui`.
- `src/setup_wizard.py` — every `corpus rag …` example → `corpus tools rag …`.
- `configs/base.example.yaml` — flashcards/quizzes/summaries `collection_prefix: rag`.
- `configs/generators.example.yaml` — same.
- `tests/unit/test_tools.py` — assert default prefix is `rag` when the section omits it.
- `tests/integration/test_generators.py` — fixtures already pass `collection_prefix="rag"`; keep them; empty-collection tests should still resolve to `rag_<name>`.

**Depends on:** none
**Blocks:** S1, DOC1

**Instructions:**
Decision R1 from OVERVIEW: one Chroma namespace, prefix `rag_`. A user who runs
`corpus tools rag ingest ./docs --collection notes` then
`corpus tools learning flashcards -c notes` must query `rag_notes`.

In each generator config:
```python
collection_prefix: str = "rag"
# and
collection_prefix=section.get("collection_prefix", "rag"),
```
Do **not** rewrite `from_dict` beyond that fallback. Do **not** edit
`generator.py` bodies (D1 will only change their EmbeddingClient import;
S1 will rewrite the rest).

Summaries CLI markdown export today does `exporter.export(summary.text, ...)`.
`SummaryGenerator.generate` returns `dict` with key `"summary"`.
`format_summary` already accepts a dict. Use `summary["summary"]` for the
exporter. Add or extend a CLI test with `CliRunner` that mocks `generate`
to return a dict and asserts the command exits 0.

Grep `src/` (not `docs/plans/`) for `corpus rag ` and `corpus rag ui` and
fix only `cli.py` and `setup_wizard.py` in this task.

**Definition of Done:**
- [ ] Flashcard/quiz/summary configs default `collection_prefix` to `"rag"`.
- [ ] `from_dict` without a prefix key also yields `"rag"`.
- [ ] Summaries CLI does not access `.text` on the generate result.
- [ ] Wizard and setup copy use `corpus tools rag …`.
- [ ] Example YAML prefixes match.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent B: C2 — Lecture pipeline uses the real VideoTranscriber API

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/orchestrations/lecture_pipeline.py` — fix constructor and `transcribe_file` call.
- `tests/test_lecture_pipeline_config.py` — mock `VideoTranscriber` with the real signature.
- `tests/unit/test_orchestrations.py` — same.

**Depends on:** none
**Blocks:** DOC1

**Instructions:**
Do **not** change `src/tools/video/transcribe.py`. The API is:

```python
class VideoTranscriber:
    def __init__(self, config: VideoConfig): ...
    def transcribe_file(self, video_path: Path) -> str: ...
```

Replace:
```python
transcriber = VideoTranscriber(self.video_config, self.db)
transcript = transcriber.transcribe_file(video_path, collection_name)
```
with:
```python
transcriber = VideoTranscriber(self.video_config)
transcript = transcriber.transcribe_file(video_path)
```
Keep `collection_name` for the temp markdown path and `RAGIngester.ingest_path`.
Leave `process_course` as a library method; do not add CLI flags.

Unit tests should patch `VideoTranscriber` and assert it was called with
one argument (config) and `transcribe_file` with the path only.

MCP `transcribe_video` is **C5**, not this task.

**Definition of Done:**
- [ ] `lecture_pipeline.py` constructs `VideoTranscriber(config)` only.
- [ ] `transcribe_file` is called with the video path only.
- [ ] Tests mock the real signature and pass.
- [ ] No regressions in existing tests.

---

### Agent C: C4 — Implement `RAGAgent.ingest_text` for handwriting

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/tools/rag/agent.py` — add `ingest_text` and `get_ingested_hashes`.
- `src/tools/rag/ingest.py` — helper used by `ingest_text` if the temp-file path is not enough to preserve `doc_id`/metadata.
- `src/tools/rag/__init__.py` — export only if the public API already lists agent methods.
- `src/tools/handwriting/cli.py` — replace the `corpus handwriting review` hint with the warnings file path.
- `tests/unit/` (new tests for agent ingest_text / get_ingested_hashes).
- `tests/tools/handwriting/test_ingest_handwriting.py` — add a test that `RAGAgent` has both methods with the handwriting signature (can still use FakeAgent for pipeline tests).

**Depends on:** none
**Blocks:** S2

**Instructions:**
Handwriting already calls:
```python
agent.ingest_text(text=..., collection=..., doc_id=..., metadata=...)
agent.get_ingested_hashes(collection)  # optional
```
Match that signature. `collection` is the user-facing name; apply
`self.config.collection_prefix` internally like ingest/retrieve already do.

Acceptable implementation: write text to a temp markdown under
`config.paths.scratch_dir`, call `RAGIngester.ingest_path`, stash
`doc_id` and extra metadata on the resulting parent/child docs. If
`ingest_path` cannot preserve `doc_id`, add `RAGIngester.ingest_text`
that builds a LangChain `Document` and runs the same parent-child split
as `ingest_path`.

`get_ingested_hashes(collection) -> set[str]` should return hashes
already stored on documents in that collection (ingest already records
`file_hash` in metadata). If the collection does not exist, return
`set()`.

CLI: when `result.low_confidence_pages > 0`, print the warnings file
path; do **not** mention a `review` command (it does not exist; R2).

Do **not** rewrite retrieval, `query()`, or strategies (S2). Do **not**
change handwriting OCR (S3).

**Definition of Done:**
- [ ] `RAGAgent.ingest_text` and `get_ingested_hashes` exist with the handwriting signature.
- [ ] Ingested text is retrievable from `rag_<collection>`.
- [ ] Missing collection → empty hash set, not an exception.
- [ ] Handwriting CLI does not mention `corpus handwriting review`.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent D: C5 — MCP uses `config.raw` and the real transcribe / generate APIs

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/mcp_server/tools/dev.py`
- `src/mcp_server/tools/learn.py`
- `src/mcp_server/tools/video.py`
- `src/mcp_server/profiles.py` — only the `VideoConfig.from_dict(...)` line(s).
- `src/mcp_server/server.py` — telemetry section from `raw`.
- `tests/unit/test_mcp_learn_tools.py`
- `tests/unit/test_mcp_dev_tools.py`
- `tests/unit/test_mcp_video.py`
- `tests/unit/test_mcp_server.py`
- `tests/test_mcp_tools.py`

**Depends on:** none
**Blocks:** S4, DOC1

**Instructions:**
Every tool config construction in `mcp_server/` must be:
```python
SomeConfig.from_dict(config.raw or config.to_dict())
```
`BaseConfig.to_dict()` still emits only `llm`/`embedding`/`database`/`paths`
and masks secrets — do not change `to_dict()`.

`transcribe_video` in `learn.py` today does
`VideoTranscriber(video_config, db)` and `transcribe_file(video_path, collection)`.
The real API is `VideoTranscriber(video_config)` and
`transcribe_file(Path(video_path))`. Return transcript text; `collection`
may remain in the JSON result for the caller but is not passed into
Whisper.

`generate_flashcards`: after building config, call
`generator.generate(validated_collection, difficulty=difficulty, count=count)`.
Do not stuff difficulty into `difficulty_levels` and then call
`generate(collection)` with defaults. Same for quiz `count`.

Do **not** collapse the `time.perf_counter` wrappers in `profiles.py`
(S4). Touch `profiles.py` only to switch `from_dict(config.to_dict())`
to `raw`.

**Definition of Done:**
- [ ] No `from_dict(config.to_dict())` remains under `src/mcp_server/` (unless preceded by `config.raw or`).
- [ ] `transcribe_video` matches `VideoTranscriber`’s real signature.
- [ ] Flashcard/quiz MCP tools pass `count`/`difficulty` into `generate()`.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent E: D1 — Delete unused RAG layers (LangChain adapter, shims, dead TUI types)

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/rag/vectorstores/langchain_adapter.py` (DELETE)
- `src/tools/rag/vectorstores/__init__.py` — stop exporting the adapter.
- `src/tools/rag/embeddings.py` (DELETE)
- `src/tools/rag/storage.py` (DELETE)
- `src/tools/rag/markdown_parser.py` (DELETE)
- `src/tools/rag/message.py` (DELETE)
- `src/tools/rag/context.py` (DELETE)
- `src/tools/flashcards/generator.py` — import `EmbeddingClient` from `tools.rag.pipeline` (import line only).
- `src/tools/quizzes/generator.py` — same.
- `src/tools/summaries/generator.py` — same.
- `tests/unit/test_rag_components.py` — import parsers/storage from `pipeline`.
- `tests/unit/test_message_metadata.py` (DELETE)
- `tests/unit/test_tui_context.py` (DELETE)
- `tests/test_dead_code_removal.py` — assert the deleted files are gone.
- `tests/test_strategies.py` — remove any import of `LangChainVectorStoreAdapter`.

**Depends on:** none
**Blocks:** S1, S2

**Instructions:**
These files are unused or 5-line re-exports. Delete them. Grep `src/` and
`tests/` for `LangChainVectorStoreAdapter`, `tools.rag.embeddings`,
`tools.rag.storage`, `tools.rag.markdown_parser`, `tools.rag.message`,
`tools.rag.context` and retarget or drop.

Keep `ChromaVectorStore` and `vectorstores/base.py` — S2 decides whether
they die. Do **not** edit `pyproject.toml` (D3). Do **not** rewrite
generator logic, only the EmbeddingClient import. Do **not** edit
`retriever.py` except if it imported the LangChain adapter (it does not).

**Definition of Done:**
- [ ] Listed files deleted; no remaining imports.
- [ ] Generators still import `EmbeddingClient` from `pipeline`.
- [ ] Dead-code tests cover the new deletes.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent F: D3 — Delete unused utils and drop unused dependencies

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/utils/secrets.py` (DELETE)
- `src/utils/tokens.py` (DELETE)
- `src/db/models.py` (DELETE)
- `src/db/__init__.py` — drop `Document` / `QueryResult` exports if present.
- `pyproject.toml` — drop unused packages.
- `uv.lock` — regenerate with `uv lock`.
- `tests/unit/test_tokens.py` (DELETE)
- `tests/test_dead_code_removal.py` — assert new deletes.
- `tests/test_security_storage.py` — only if it imported `SecretManager`; retarget or drop those cases.

**Depends on:** none
**Blocks:** V1

**Instructions:**
Repo-wide grep before deleting: `SecretManager`, `from utils.secrets`,
`from utils.tokens`, `from db.models`, `from db import Document`.
Production `src/` should have zero hits (auth.py’s `import secrets` is
the stdlib module — leave it).

From `pyproject.toml` dependencies and the `server` extra, remove
`langchain`, `langchain-community`, `langchain-chroma` (keep
`langchain-core` and `langchain-text-splitters`). Remove `keyring` and
`cryptography` only if the grep shows no remaining `src/` import.
Do **not** add newly-unused packages to `DEP002` — delete them.

Run `uv lock` so CI `--check` passes. Leave torch / sentence-transformers
/ faster-whisper alone.

**Definition of Done:**
- [ ] `secrets.py`, `tokens.py`, `db/models.py` gone; no production imports.
- [ ] Unused packages removed from `pyproject.toml`; `uv.lock` synced.
- [ ] `uv run deptry src` does not fail because of this change.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent G: S3 — Unify vision OCR client

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/tools/ocr_client.py` (NEW) — shared `ocr_image(...)`.
- `src/tools/video/ocr.py` — call the shared helper; keep SLIDE/CHALKBOARD prompts.
- `src/tools/handwriting/ocr.py` — call the shared helper; keep HANDWRITING_PROMPT.
- `tests/unit/test_ocr.py` — cover both call sites via the helper (httpx/ollama mocked).
- `tests/tools/handwriting/` — update any OCR tests that patched `ollama.chat` to patch the shared helper or the new module.

**Depends on:** none
**Blocks:** none (nice-to-have before DOC1)

**Instructions:**
Video uses `httpx` against `{endpoint}/api/chat` with `images: [b64]`.
Handwriting uses `ollama.chat`. One function:

```python
def ocr_image(
    image_path: Path,
    prompt: str,
    *,
    model: str,
    endpoint: str = "http://localhost:11434",
    timeout: float = 120.0,
) -> str:
```

Pick one HTTP client (httpx is already a core dep; prefer it so
handwriting does not need a different stack). Preserve skip-on-huge-file
behavior from video OCR. Do not change ingest orchestrators or prompts’
text. Do not add Chroma writes to video OCR (non-goal).

**Definition of Done:**
- [ ] Single shared OCR HTTP helper used by video and handwriting.
- [ ] Prompts remain in their original modules.
- [ ] Tests mock the helper/client and pass.
- [ ] No regressions in existing tests.

---

## What this wave unblocks

Sprint 2: S1 (needs C1 + D1), S2 (needs C4 + D1), S4 (needs C5).
