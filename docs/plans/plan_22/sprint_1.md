# Sprint 1 — Kernel, husk delete, first-run, generators

**Plan:** docs/plans/plan_22/OVERVIEW.md
**Wave:** 1 of 3
**Can run in parallel with:** none as a sprint; agents inside this wave may run in parallel
**Must complete before:** Sprint 2 (K2, K3)

Branch from post-plan-21 `plan-21/sprint-1` (or current main if 21 is merged).

---

## Agents in This Wave

### Agent A: K1 — Corpus kernel

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/kernel.py` (NEW) — `Corpus` class
- `pyproject.toml` — add `"kernel"` to `[tool.setuptools] py-modules`
- `tests/test_kernel.py` (NEW)

**Depends on:** none
**Blocks:** K2, K3

**Instructions:**
Create `src/kernel.py`:

```python
class Corpus:
    def __init__(self, config: RAGConfig, db: DatabaseBackend): ...

    @classmethod
    def from_config_path(cls, path: str | Path = "configs/base.yaml") -> Corpus:
        cfg, db = load_cli_db(path, RAGConfig)
        return cls(cfg, db)

    def ingest_path(self, path: str | Path, collection: str):
        return RAGIngester(self.config, self.db).ingest_path(Path(path), collection)

    def ingest_text(self, text: str, collection: str, *, doc_id=None, metadata=None):
        return RAGAgent(self.config, self.db).ingest_text(...)

    def ask(self, query: str, collection: str, *, top_k: int | None = None) -> str:
        return RAGAgent(self.config, self.db).query(query, collection, top_k=top_k)

    def summarize(self, collection: str, *, topic: str | None = None, length: str = "medium") -> dict:
        from tools.summaries import SummaryConfig, SummaryGenerator
        s_cfg = SummaryConfig.from_dict(self.config.raw or self.config.to_dict())
        if length:
            s_cfg.summary_length = length
        return SummaryGenerator(s_cfg, self.db).generate(collection, topic)

    def sample(self, collection: str, *, query: str, n: int) -> list[str]:
        return sample_documents(self.db, self.config, collection, query_text=query, n_results=n)

    def complete(self, prompt: str) -> str:
        return complete_prompt(self.config, prompt)
```

Use lazy imports inside methods if that avoids import-time TUI/transformers cost; keep `from_config_path` cheap.

Tests (`tests/test_kernel.py`):
- `from_config_path` loads a tmp YAML with persistent Chroma.
- `ingest_text` then `sample` returns the text (mock embeddings if needed; follow `tests/unit/test_rag_agent_ingest.py` patterns).
- `ask` is patched at `RAGAgent.query` or the LLM backend so no live model is required.
- `summarize` patched at generator or `complete_prompt`.
- Collection name passed to ingest/ask is the user-facing name (`notes`), not `rag_notes`.

Do not edit MCP, CLI, or generators.

**Definition of Done:**
- [ ] `Corpus` exposes ingest_path, ingest_text, ask, summarize, sample, complete.
- [ ] `from_config_path` works with `configs/base.yaml` layout.
- [ ] `kernel` is a setuptools py-module.
- [ ] `tests/test_kernel.py` passing; no live LLM.
- [ ] No regressions in existing tests.

---

### Agent B: H1 — Delete empty vectorstores package

**Complexity:** S
**Estimated time:** 0.5 hours
**Files to modify:**
- `src/tools/rag/vectorstores/` (DELETE the directory, including `__init__.py`)
- `src/tools/rag/README.md` — remove the vectorstores tree line
- `tests/test_dead_code_removal.py` — assert the directory is gone

**Depends on:** none
**Blocks:** none

**Instructions:**
The package is a leftover husk (`__all__: list[str] = []`). Delete it. Grep `src/` for `tools.rag.vectorstores` and remove any import (there should be none). Extend `test_plan21_unused_layers_deleted` (or add `test_plan22_vectorstores_package_deleted`) so `Path("src/tools/rag/vectorstores").exists()` is false.

Do not delete `DatabaseBackend` or strategy files. Do not rewrite retrieval.

**Definition of Done:**
- [ ] `src/tools/rag/vectorstores/` does not exist.
- [ ] Dead-code test fails if the directory is reintroduced.
- [ ] RAG README no longer lists vectorstores as a live package.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent C: F1 — First-run wizard, doctor, Compose healthcheck

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/setup_wizard.py` — port 8001, port field, model input, TUI launch, finish-screen CLI copy
- `src/tools/rag/doctor.py` — persistent vs HTTP
- `.docker/docker-compose.yml` — Chroma healthcheck `/api/v2/heartbeat`
- `tests/unit/test_setup_wizard_config.py`
- `tests/unit/test_doctor.py` (NEW)

**Depends on:** none
**Blocks:** D1 (docs)

**Instructions:**
1. `WizardConfig.chroma_port` default `8001`. On `ChromaHostScreen`, add an Input for port (default 8001); persist on Continue. `save_config` already writes `port`.
2. After backend Continue, collect LLM model (Input, prefilled with current default) and embedding model (Input, prefilled `embeddinggemma`). Do not add extra screens if a couple of Inputs on BackendScreen fit; otherwise one small “Models” screen before chroma.
3. Finish Markdown: `corpus tools rag ingest ./vault --collection notes` (positional path, **not** `--path`); `corpus tools rag query "your question" -c notes`; keep HTTP compose hint with `-f .docker/docker-compose.yml`.
4. Extract TUI launch from `RAGApp()` into a helper used by `run_setup_wizard`: same as `tools.rag.cli.ui` (`load_cli_db` + `RAGAgent` + `RAGApp(agent, collection=None)`). Empty collections already notify and exit — acceptable.
5. Doctor: if `config.database.mode == "persistent"`: `ChromaDBBackend(config.database).list_collections()` and report OK with count; do **not** HTTP-heartbeat. If `http`: keep `/api/v2/heartbeat` then list collections.
6. Compose `chromadb.healthcheck.test`: `http://localhost:8000/api/v2/heartbeat` (container port is 8000).

Tests: wizard default port 8001; HTTP generated compose uses 8001; persistent doctor passes with only a tmp persist_directory (no server); HTTP doctor still fails when nothing listens. Do not run the Textual app.

**Definition of Done:**
- [ ] HTTP wizard default port is 8001 and is user-editable.
- [ ] Persistent `run_doctor` does not require HTTP Chroma.
- [ ] Launch TUI helper passes `(agent, collection)` into `RAGApp`.
- [ ] Finish-screen commands match live Click (no `--path`).
- [ ] Repo Compose Chroma healthcheck is v2.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent D: G1 — Generators use `complete_prompt`

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/flashcards/generator.py`
- `src/tools/quizzes/generator.py`
- `src/tools/summaries/generator.py`
- `tests/unit/test_generation.py` (patch `complete_prompt` if tests still patch `create_backend` on generator modules)
- `tests/unit/test_tool_generators.py` only if they construct backends

**Depends on:** none
**Blocks:** none

**Instructions:**
Remove `from llm import create_backend` and `self.llm_backend = create_backend(...)` from the three generators. Replace `self.llm_backend.complete(prompt)` with `complete_prompt(self.config, prompt)` from `tools.generation`. Summaries keyword/outline helpers that call the LLM must use the same helper.

Do **not** `import kernel`. Keep `generate()` signatures and return types. Existing tests that patch `tools.flashcards.generator.create_backend` or `EmbeddingClient` need retargeting to `tools.generation.complete_prompt` and whatever embed path `sample_documents` uses (already `tools.generation`).

**Definition of Done:**
- [ ] No `create_backend` in the three generator modules.
- [ ] Completions go through `complete_prompt`.
- [ ] Tests updated and passing.
- [ ] No regressions in existing tests.

---

## What this wave unblocks

K1 unblocks K2 (CLI aliases) and K3 (`simple` MCP). F1 unblocks D1 first-run docs. H1 and G1 are complete after this wave.
