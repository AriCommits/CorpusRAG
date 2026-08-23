# Sprint 2 — Flatten CLI and simple MCP

**Plan:** docs/plans/plan_22/OVERVIEW.md
**Wave:** 2 of 3
**Can run in parallel with:** agents inside this wave (K2 ‖ K3) after Wave 1
**Must complete before:** Sprint 3 (D1)

Requires Wave 1 **K1** merged (`src/kernel.py` exists).

---

## Agents in This Wave

### Agent A: K2 — Top-level ingest / ask / summarize CLI

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/cli.py` — root commands `ingest`, `ask`, `summarize`
- `src/tools/rag/cli.py` — ingest and query delegate to `Corpus`
- `cli.txt` — top-level Commands list (encoding: file may be UTF-16; keep `test_cli_txt_matches_live_command_tree` green)
- `tests/unit/test_rag_cli.py` — still pass; they invoke nested commands
- `tests/unit/test_kernel_cli.py` (NEW) — Click runner on top-level ingest/ask/summarize

**Depends on:** K1
**Blocks:** D1

**Instructions:**
On the root `corpus` group add:

```text
corpus ingest PATH --collection NAME
corpus ask QUERY --collection NAME
corpus summarize --collection NAME [--topic ...] [--length short|medium|long]
```

Use `-c` / `--collection` required, same as nested RAG CLI. Implementation:

```python
from kernel import Corpus
c = Corpus.from_config_path(config)
c.ingest_path(path, collection)
# ask → echo c.ask(...)
# summarize → echo the summary dict's "summary" (and optionally keywords)
```

`--config` / `-f` default `configs/base.yaml`.

In `tools.rag.cli` `ingest` and `query`, construct `Corpus` the same way instead of `RAGIngester` / `RAGAgent` directly. Leave `sync`, `chat`, `ui` on the old types.

Do **not** remove `corpus tools rag ingest` or `corpus tools rag query`. Do not add plugin discovery.

`cli.txt` is asserted against `corpus.list_commands`. After adding three names, update that file. If it is UTF-16, rewrite in the same encoding the test helper accepts (`_read_text_any`).

Tests: CliRunner invoke `ingest` missing collection → non-zero; `ask` with mocked `Corpus.ask`; summarize mocked `Corpus.summarize`. Nested ingest still works (existing tests).

**Definition of Done:**
- [ ] `corpus ingest`, `corpus ask`, `corpus summarize` exist on the root group.
- [ ] Nested `corpus tools rag ingest|query` call `Corpus`.
- [ ] `cli.txt` matches the live top-level set.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent B: K3 — MCP `simple` profile + kernel call sites

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `src/mcp_server/profiles.py` — `simple` + `register_simple_tools`
- `src/mcp_server/server.py` — default profile `simple`; argparse choices
- `src/mcp_server/tools/dev.py` — `rag_query`, `rag_ingest`, `store_text` via `Corpus`
- `src/mcp_server/tools/learn.py` — `generate_summary` via `Corpus`
- `tests/unit/test_mcp_profiles.py`
- `tests/unit/test_mcp_server.py`
- `tests/unit/test_mcp_dev_tools.py` / `test_mcp_learn_tools.py` as needed for constructor patches

**Depends on:** K1
**Blocks:** D1

**Instructions:**
`VALID_PROFILES = ("simple", "dev", "learn", "full")`.

```python
def register_simple_tools(...):
    # rag_ingest, rag_query, store_text, list_collections from register_dev_tools
    # but ONLY those four + generate_summary
```

Cleanest: factor the five `@mcp.tool` closures, call them from `register_simple_tools`. Do **not** register flashcards, quizzes, video, telemetry SQL, or `rag_retrieve` on `simple`. `list_collections` stays. Resource `collections://list` may be registered on simple (same as dev) — optional; if you add it, tests should allow it (resources ≠ tools).

`register_profile`:
- `simple` → `register_simple_tools` only
- `dev` / `learn` / `full` as today

Default in `create_mcp_server` and argparse: `simple`.

Kernel wiring in `dev.py` / `learn.py`:

```python
from kernel import Corpus
from tools.rag.config import RAGConfig
rag_config = RAGConfig.from_dict(config.raw or config.to_dict())
corpus = Corpus(rag_config, db)
corpus.ask(...) / ingest_path / ingest_text / summarize(...)
```

Keep returning the same dict shapes (`status`, `response`, `summary`, …) so existing unit tests stay valid. `generate_flashcards` / quiz / transcribe stay on their generators.

Tests:
- `simple` tool names == `{rag_ingest, rag_query, store_text, list_collections, generate_summary}` (and `collection_info` **out** unless you have a strong reason — plan says not to include it).
- `simple` must not include `generate_flashcards`, `video_ingest_local`.
- `full` still has `rag_query` and `generate_flashcards`.
- `create_mcp_server` default profile is `simple`.
- Invalid profile still raises.

**Definition of Done:**
- [ ] `--profile simple` registers exactly the five tools above.
- [ ] Default MCP profile is `simple`.
- [ ] Query / ingest / store_text / summarize MCP functions use `Corpus`.
- [ ] `dev` / `learn` / `full` membership unchanged aside from kernel internals.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

## What this wave unblocks

D1 (docs) can describe live commands and the simple profile.
