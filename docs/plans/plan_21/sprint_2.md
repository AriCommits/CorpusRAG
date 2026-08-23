# Sprint 2 — Collapse Copies

**Plan:** docs/plans/plan_21/OVERVIEW.md
**Wave:** 2 of 4
**Can run in parallel with:** all agents in this wave (S1, S2, S4 touch disjoint files **after** Wave 1 is merged)
**Must complete before:** Sprint 3 (DOC1 describes the simplified architecture)

Branch from post-Wave-1 `main`. Do not start until C1, C2, C4, C5, D1, D3, S3 are merged.

---

## Agents in This Wave

### Agent A: S1 — Collapse flashcards / quizzes / summaries onto a shared helper

**Complexity:** L
**Estimated time:** 4 hours
**Files to modify:**
- `src/tools/generation.py` (NEW) — sample collection + LLM complete.
- `src/tools/flashcards/generator.py` — use the helper; keep parse/format/export.
- `src/tools/quizzes/generator.py` — same; **stop padding** missing questions with placeholder Q&A.
- `src/tools/summaries/generator.py` — same.
- `src/tools/flashcards/config.py` — optional `from_dict` helper from BaseConfig.
- `src/tools/quizzes/config.py` — same.
- `src/tools/summaries/config.py` — same.
- `src/tools/flashcards/__init__.py` — drop tiktoken gate if unused.
- `src/tools/quizzes/__init__.py` — same.
- `src/tools/summaries/__init__.py` — same.
- `src/config/base.py` — optional helper to copy llm/embedding/database/paths + overlay a named section; **only this task edits this file**.
- `src/tools/summaries/cli.py` — only if the C1 dict fix must move with a new return type (keep dict).
- `tests/integration/test_generators.py`
- `tests/unit/test_tool_generators.py`
- `tests/test_optional_extras.py` — if `GENERATORS_AVAILABLE` goes away, assert imports still work without tiktoken.

**Depends on:** C1, D1
**Blocks:** DOC1, V1

**Instructions:**
Wave 1 already set `collection_prefix` default to `"rag"` and pointed
EmbeddingClient imports at `pipeline`. Do not revert either.

New `src/tools/generation.py` should own:
1. Resolve `f"{config.collection_prefix}_{collection}"`.
2. Existence / empty-collection errors that mention
   `corpus tools rag ingest --collection {collection}`.
3. Sample texts via `EmbeddingClient` + `db.query`.
4. `create_backend(config.llm.to_backend_config()).complete(prompt)`.

Each generator keeps its `PromptTemplates.*` call, regex parse, and
export/format methods. Quiz/flashcard generators must **not** invent
placeholder questions to hit `count`; return the parsed list (tests that
assert padding must be updated).

Tiktoken: grep `src/` for `tiktoken` / `GENERATORS_AVAILABLE`. If only
the three `__init__.py` stubs use it, delete the stubs and import the
real classes unconditionally. Leave `pyproject.toml` extras alone (D3
owns packaging; `generators` extra may stay even if empty of unique
deps — do not add new extras).

Preserve public class names (`FlashcardGenerator.generate(...)` etc.)
so CLI and MCP keep working.

**Definition of Done:**
- [ ] Shared sampling/LLM helper used by all three generators.
- [ ] No fake Q&A padding in quizzes/flashcards.
- [ ] Prefix remains `rag_` (C1).
- [ ] Tiktoken gate gone if tiktoken is unused in `src/`.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent B: S2 — One staged retrieval strategy + parent-store isolation

**Complexity:** L
**Estimated time:** 4 hours
**Files to modify:**
- `src/tools/rag/strategies/staged.py` (NEW)
- `src/tools/rag/strategies/hybrid.py` — thin wrapper or delete if registry points at staged.
- `src/tools/rag/strategies/semantic.py` — same.
- `src/tools/rag/strategies/keyword.py` — same.
- `src/tools/rag/strategies/__init__.py`
- `src/tools/rag/strategies/base.py` — keep `RetrievedDocument` / protocol.
- `src/tools/rag/retriever.py` — construct staged strategy; may take `db` instead of `ChromaVectorStore`.
- `src/tools/rag/ingest.py` — write `collection_name` on parent Documents; namespace parent files.
- `src/tools/rag/pipeline/storage.py` — optional per-collection subdirectory support.
- `src/tools/rag/config.py` — honor or delete dead knobs (`reranking.*`, `top_k_semantic`, `top_k_bm25`, `vectorstore.*`, `parent_store.type`).
- `src/tools/rag/vectorstores/chroma_adapter.py` (DELETE if strategies call `db` directly)
- `src/tools/rag/vectorstores/base.py` (DELETE if unused)
- `src/tools/rag/vectorstores/__init__.py`
- `src/tools/rag/cli.py` — `query` currently calls `agent.query` then `agent.retrieve`; retrieve once.
- `src/tools/rag/agent.py` — delete the `stream=True` branch that still calls `complete()`. C4 added methods here; do not remove `ingest_text` / `get_ingested_hashes`.
- `configs/rag.example.yaml` — match whatever knobs remain.
- `configs/base.example.yaml` — **`rag:` section only** (C1 already set generator prefixes).
- `tests/test_strategies.py`
- `tests/unit/test_rag_components.py`

**Depends on:** D1, C4
**Blocks:** DOC1, V1

**Instructions:**
One `StagedStrategy` with flags/name:
- `hybrid`: vector + BM25 + RRF + rerank
- `semantic`: vector + rerank
- `keyword`: BM25 only

Keep `get_strategy("hybrid"|"semantic"|"keyword")` working. Lazy-import
`CrossEncoder` inside rerank. Cache embedder models on the instance
(do not construct `SentenceTransformer` per batch if the client already
does — fix that in the strategy/embedder path you touch).

Parent isolation (R6):
- On every parent `Document` written in `ingest.py`, set
  `metadata["collection_name"]` to the **unprefixed** user collection name.
- Store parent JSON under `parent_store/<collection>/` (sanitize the
  segment). `LocalFileStore` may take that path from ingest/retriever.
- BM25: `doc.metadata.get("collection_name") == collection` only.
  Delete `or not doc.metadata.get("collection_name")`.
- No migration of old parent files; they simply stop matching.

Dead config: either wire `reranking.enabled` / `reranking.model` /
`retrieval.top_k_semantic` / `top_k_bm25` **or** remove them from
`RAGConfig` + example YAML in this task. Same for `vectorstore.backend`
/ `langchain_class` (adapter already gone in D1) and `parent_store.type`
if still ignored.

If `ChromaVectorStore` is still a pass-through, delete it and use
`DatabaseBackend` from strategies. Update tests that imported the adapter.

CLI `query` in `src/tools/rag/cli.py` runs retrieval twice — keep the
generated answer, drop the extra `agent.retrieve` unless you still need
the doc list; if you need both, get docs from the agent’s last retrieve
or return them from `query`. Do not double-run hybrid.

**Definition of Done:**
- [ ] One staged implementation behind hybrid/semantic/keyword names.
- [ ] Parents isolated per collection; BM25 cannot see other collections’ parents.
- [ ] No leftover dead RAG config knobs (wired or deleted).
- [ ] CLI query does not run retrieval twice.
- [ ] `ingest_text` from C4 still works.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent C: S4 — One MCP telemetry decorator

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/mcp_server/telemetry.py` (NEW) — decorator/wrapper.
- `src/mcp_server/profiles.py` — use it; delete the 15 copied timer blocks.
- `tests/unit/test_mcp_profiles.py`
- `tests/unit/test_mcp_server.py`
- `tests/unit/test_telemetry.py` — if the wrapper should be unit-tested here.

**Depends on:** C5
**Blocks:** DOC1, V1

**Instructions:**
Wave 1 already switched `from_dict` to `config.raw or config.to_dict()`
and fixed transcribe/generate call sites. Do **not** revert those.

Replace:
```python
start = time.perf_counter()
result = foo(...)
if store:
    store.log("foo", (time.perf_counter() - start) * 1000, ...)
return result
```
with one wrapper, e.g. `with_telemetry(store, name)` or a decorator that
logs duration, `input_size`, and `success` (`result.get("status") != "error"`
when the result is a dict). Tool implementations stay in `tools/*.py`.

Preserve profile membership (`dev` / `learn` / `full`) and tool names.
`study_session_prompt` can stay as-is.

**Definition of Done:**
- [ ] Repeated timer blocks gone from `profiles.py`.
- [ ] C5 behavior (raw config, transcribe signature, generate args) preserved.
- [ ] Profiles still register the same tools.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

## What this wave unblocks

Sprint 3: DOC1 can describe one collection namespace, staged retrieval,
shared generators, and a decorator-based MCP server.
