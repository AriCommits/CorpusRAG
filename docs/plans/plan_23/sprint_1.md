# Sprint 1 — Fast CLI help

**Plan:** docs/plans/plan_23/OVERVIEW.md
**Wave:** 1 of 2 (Feature 1 of 2)
**Can run in parallel with:** Sprint 2 Phases 1–3 (audio extract, discovery, queue, `process_course`). Do **not** start Sprint 2 **C3** (video CLI wiring) until Agent B (A2) is merged — both edit `src/tools/video/cli.py`.
**Must complete before:** Sprint 2 task **C3** only. A4 is the last step of this sprint, not a gate for audio work.

This sprint is the CLI-startup feature. Goal: `corpus --help` / `corpus tools --help` / `corpus tools video --help` / `corpus tools rag --help` do not import `chromadb`, `textual`, `torch`, `faster_whisper`, `sentence_transformers`, or `transformers`. Command names and flags do not change.

**Phase 1 (parallel):** A1, A2, A3.
**Phase 2 (serial, after Phase 1 merge):** A4.

Branch from `plan-23/dev`.

---

## Agents in This Wave

### Agent A: A1 — LazyGroup help without importing subcommands

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/cli_lazy.py` — store short help; override `format_commands`
- `src/cli.py` — tuple short-help on root lazy map
- `src/tools/cli.py` — tuple short-help on tools lazy map
- `src/tools/learning/cli.py` — tuple short-help on learning lazy map

**Depends on:** none
**Blocks:** A4

**Instructions:**

Click `Group.format_commands` calls `get_command` for every listed name so it can read `short_help`. That is why `LazyGroup` still imports RAG/video/db on `--help`. Fix the group, not the install extras.

In `src/cli_lazy.py`:

- Type the map as `dict[str, str | tuple[str, str]]`. A plain string is the import path (empty short help). A tuple is `(import_path, short_help)`.
- Add `_spec(name) -> tuple[str, str]` that normalizes both shapes.
- `_load_lazy` uses `_spec` for the import path. Keep the existing `ImportError` stub group.
- `list_commands` stays name-only. Do **not** call `_load_lazy` from `list_commands` or `format_commands`.
- Override `format_commands(self, ctx, formatter)`:
  - For each name in `list_commands`:
    - If it is lazy: use the stored short help (do not import).
    - Else: `cmd = super().get_command(ctx, name)`; skip `None` / `hidden`; use `cmd.get_short_help_str()`.
  - Write a `Commands` section with `formatter.write_dl(rows)` the same way Click does.
- `get_command` still lazy-loads when the user actually runs a subcommand.

Fill short-help from the **current** command docstrings (first line):

Root (`src/cli.py`):

- `tools` → `CorpusRAG tools — RAG, video, handwriting, summaries, and learning.`
- `db` → copy from `db.management:db` docstring (open the file; do not import it from `cli.py`).
- `collections` → `Manage vector database collections.`
- `dev` → copy from `cli_dev:dev` docstring.
- `orchestrate` → `Orchestration workflows for CorpusRAG.`

Tools (`src/tools/cli.py`): `rag`, `video`, `handwriting`, `summaries`, `learning` — copy each group's first docstring line.

Learning (`src/tools/learning/cli.py`): `flashcards`, `quizzes` — same.

Do not move implementation imports. That is A2/A3. After A1 alone, `corpus --help` must not import `tools.rag.cli` or `tools.video.cli`. It may still import `db.management` until A2/A3.

**Definition of Done:**
- [ ] `format_commands` never calls `_load_lazy`.
- [ ] String and tuple values both work in `lazy_subcommands`.
- [ ] Root / tools / learning maps have short-help tuples.
- [ ] Existing `corpus --help` still lists `tools`, `db`, `collections`, `dev`, `orchestrate`, `setup`, `benchmark`, `doctor`.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent B: A2 — Defer heavy imports in Click modules

**Complexity:** M
**Estimated time:** 2.5 hours
**Files to modify:**
- `src/tools/rag/cli.py` — drop module-level RAG/TUI/`cli_common`
- `src/tools/video/cli.py` — drop module-level transcribe/clean/augment/`cli_common`
- `src/tools/summaries/cli.py`
- `src/tools/flashcards/cli.py`
- `src/tools/quizzes/cli.py`
- `src/tools/handwriting/cli.py`
- `src/db/management.py` — drop module-level numpy / chroma / `cli_common`
- `src/db/collections_cli.py` — drop module-level rich / chroma / `cli_common`
- `src/orchestrations/cli.py` — drop module-level `cli_common` if present

**Depends on:** none
**Blocks:** A4, C3 (Sprint 2)

**Instructions:**

Module-level imports in these files must be `click`, plus `pathlib` / `typing` / `cli_lazy` as needed. Everything else (`cli_common`, `RAGAgent`, `RAGApp`, `VideoTranscriber`, `TranscriptCleaner`, `TranscriptAugmenter`, generators, `numpy`, `ChromaDBBackend`, `rich`) moves into the command function body or a helper that is only called from the body.

`src/tools/video/cli.py` is the important one: today `corpus tools video --help` imports the transcriber and cleaner. **Only move imports.** Do not rewire `transcribe` / `pipeline` to the queue (C3). Do not add `--workers` or `--no-recursive`. Keep command names, options, help text, and runtime behavior identical.

`src/tools/rag/cli.py` today does `from .agent import RAGAgent` and `from .tui import RAGApp` at import time (Textual + retrieval stack). Import those inside `ui` / `query` / `chat` / whichever command uses them. `ingest` already imports `kernel` inside the function — keep that pattern.

If a test patches `tools.video.cli.VideoTranscriber` (or similar), retarget the patch to `tools.video.transcribe.VideoTranscriber` or the in-function import site so the test still hits the call.

`db.management` currently imports `numpy` and `ChromaDBBackend` at module level so `corpus --help` pays Chroma. Move them. Keep Zip Slip helpers and command signatures unchanged.

**Definition of Done:**
- [ ] Listed CLI modules do not import chromadb / textual / torch / faster_whisper / RAG / video implementation at module level.
- [ ] `corpus tools video --help` and `corpus tools rag --help` still show the same command names and flags.
- [ ] `tests/test_cli_docs_consistency.py` and `tests/unit/test_cli.py` / `tests/unit/test_video_cli.py` pass (patch sites updated if needed).
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent C: A3 — Stop `cli_common` and `db` from importing Chroma at import time

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/cli_common.py` — `load_cli_config` must not import Chroma
- `src/db/__init__.py` — lazy `ChromaDBBackend`

**Depends on:** none
**Blocks:** A4

**Instructions:**

`src/cli_common.py` today:

```python
from db import ChromaDBBackend
```

`load_cli_config` only needs `config.load_config`. Remove the Chroma import from module level. Inside `load_cli_db`, import `ChromaDBBackend` locally (or `from db import ChromaDBBackend` after `__getattr__` exists).

`src/db/__init__.py` today imports `.chroma` immediately. Mirror `tools.rag.__getattr__` / `orchestrations.__getattr__`:

- Eager-export `DatabaseBackend` from `.base` (cheap).
- Lazy-export `ChromaDBBackend` on first attribute access.
- Keep `__all__ = ["ChromaDBBackend", "DatabaseBackend"]`.

Do not edit `src/db/chroma.py`. `from db import ChromaDBBackend` and `from db import DatabaseBackend` must keep working (`tests/unit/test_tools.py`, orchestrations tests, etc.).

**Definition of Done:**
- [ ] Importing `cli_common` does not import `chromadb`.
- [ ] `from db import DatabaseBackend` does not import `chromadb`.
- [ ] `from db import ChromaDBBackend` still returns the real class.
- [ ] `load_cli_db` still returns `(cfg, ChromaDBBackend(...))`.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent A (Phase 2): A4 — CLI startup hygiene tests

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `tests/unit/test_cli_startup.py` (NEW)
- `tests/unit/test_cli.py` — only if A1 short-help wording breaks an assertion

**Depends on:** A1, A2, A3
**Blocks:** none

**Instructions:**

Run this **after A1+A2+A3 are merged** on the sprint branch. Do not write the blacklist test against a tree that still imports Chroma on help — it will fail and you will weaken the assertion.

`tests/unit/test_cli_startup.py` must spawn a **subprocess** (`PYTHONPATH=src`, same interpreter). The parent pytest process may already have imported chromadb; that must not count.

For each of:

- `["--help"]`
- `["tools", "--help"]`
- `["tools", "video", "--help"]`
- `["tools", "rag", "--help"]`

assert:

1. Exit code 0.
2. After help, `sys.modules` does **not** contain: `chromadb`, `textual`, `torch`, `faster_whisper`, `sentence_transformers`, `transformers`.
3. Help stdout still contains the relevant command names (`tools` / `video` / `rag` / `transcribe` as applicable).

Do **not** assert a wall-clock budget (CI noise). A comment may note the local target is sub-second.

Implementation sketch: a small helper module string run with `subprocess.run([sys.executable, "-c", script], env=..., cwd=repo)`. The script uses `click.testing.CliRunner` on `cli.corpus`, then prints a JSON payload `{exit, leaked, output_ok}`.

If A1 changed short-help wording, update `tests/unit/test_cli.py` assertions only as needed. Do not expand CLI surface.

**Definition of Done:**
- [ ] Subprocess tests for the four help paths.
- [ ] Banned modules listed above are asserted absent.
- [ ] Help still lists the lazy command names.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests
