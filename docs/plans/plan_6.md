# Consolidated Plan: CI Fixes, Sync, Collection UX, Export, and Benchmarking

**Date:** 2026-04-17  
**Status:** Pending  
**Scope:** Merges Plan 6 (CI lint fixes, sync command, README) and Plan 7 (slash commands, collection management, export, sync feedback, benchmarking) into a single dependency-ordered implementation plan.

---

## Phase 1: Fix All Ruff Lint & Format Errors

**Goal:** Unblock CI. This is the foundation — nothing else matters if CI is red.

### 1.1 — Fix `SecurityError` undefined name errors (5 occurrences)

**File:** `src/mcp_server/server.py`

`SecurityError` is caught in 5 `except` clauses (lines 147, 189, 241, 294, 342) but never imported at module level. The class lives in `src/utils/security.py`.

- [ ] Add `from utils.security import SecurityError` to the top-level imports of `server.py`
- [ ] Remove the redundant local import in `rag_ingest()` (line 101: `from utils.security import SecurityError, validate_file_path`) — only keep `validate_file_path` there since `SecurityError` will now be module-level.

### 1.2 — Fix E402 (module-level import not at top of file) in `retriever.py`

**File:** `src/tools/rag/retriever.py`

Lines 14–21 import after executable statements (`disable_progress_bars()`, `set_verbosity_error()`). Ruff flags these as E402.

**Fix:** Add `"src/tools/rag/retriever.py"` to the `per-file-ignores` section in `pyproject.toml`:

```toml
[tool.ruff.lint.per-file-ignores]
"tests/test_smoke.py" = ["E402"]
"src/tools/rag/retriever.py" = ["E402"]
```

### 1.3 — Run `ruff format` to fix ~40 formatting violations

```bash
ruff format src/ tests/
```

- [ ] Run `ruff format src/ tests/`
- [ ] Verify: `ruff format --check src/ tests/` reports 0 issues
- [ ] Verify: `ruff check src/ tests/` reports 0 errors

---

## Phase 2: TUI Slash Command Router

**Goal:** Build the interception and dispatch layer that all subsequent TUI features register into. This is the foundation for Phases 4–7.

### 2.1 — Slash Command Router

**File:** `src/tools/rag/slash_commands.py` (new)

```python
@dataclass
class SlashCommand:
    name: str
    args: list[str]
    raw: str

@dataclass
class SlashCommandResult:
    type: Literal["text", "screen", "toast", "error", "stream"]
    content: str | None = None
    screen: Screen | None = None
    toast_message: str | None = None

class SlashCommandRouter:
    """Intercept and route slash commands before LLM dispatch."""

    def is_slash_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def parse(self, text: str) -> SlashCommand:
        parts = text.strip().lstrip("/").split()
        return SlashCommand(name=parts[0], args=parts[1:], raw=text)

    def dispatch(self, command: SlashCommand) -> SlashCommandResult:
        handler = self._registry.get(command.name)
        if handler is None:
            return SlashCommandResult(type="error", content=f"Unknown command: /{command.name}\nType /help to see available commands.")
        return handler(command.args)
```

### 2.2 — Decorator-based registration pattern

```python
_registry: dict[str, Callable] = {}

def slash_command(name: str, description: str):
    def decorator(fn: Callable) -> Callable:
        _registry[name] = fn
        return fn
    return decorator
```

Each feature registers its own commands colocated with feature code.

### 2.3 — Global commands

Register these in `slash_commands.py` directly:

| Command | Result type | Action |
|---------|-------------|--------|
| `/help` | `text` | List all registered slash commands with descriptions |
| `/clear` | `text` | Clear chat history for current session |
| `/ask <question>` | `stream` | Explicit RAG query (same as typing without `/`) |

### 2.4 — Wire into TUI input handler

**File:** `src/tools/rag/tui.py`

In the chat input `on_submit` handler, add interception before LLM dispatch:

```python
async def on_chat_input_submitted(self, message: str) -> None:
    if self.router.is_slash_command(message):
        result = self.router.dispatch(self.router.parse(message))
        await self.handle_slash_result(result)
        return
    # existing LLM dispatch continues here...
    await self.send_to_llm(message)
```

---

## Phase 3: RAGSyncer + `corpus rag sync` CLI Command

**Goal:** Extract change-detection logic from `ingest` into a dedicated sync system. This unblocks Phase 5 (sync feedback in TUI).

### 3.1 — Add `source_file_name` metadata field

**File:** `src/tools/rag/ingest.py`

In `ingest_path()`, around line 172–175 where `parent_metadata` is built:

```python
parent_metadata["source_file"] = relative_path
parent_metadata["source_file_name"] = file_path.name   # <-- NEW
parent_metadata["parent_index"] = parent_idx
parent_metadata["file_hash"] = file_hash
```

### 3.2 — Create sync logic

**File:** `src/tools/rag/sync.py` (new)

```python
@dataclass(frozen=True)
class SyncResult:
    collection: str
    new_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]
    unchanged_files: list[str]
    chunks_added: int
    chunks_removed: int
```

**Algorithm:**

1. Enumerate all supported files under the vault path (reuse `RAGIngester._iter_source_files()`).
2. For each file, compute SHA-256 hash of its content.
3. Query the collection for all unique `(source_file, file_hash)` pairs currently stored.
4. Compare:
   - **New:** file exists on disk but `source_file` not in DB.
   - **Modified:** file exists on disk and in DB, but hash differs.
   - **Unchanged:** file exists on disk and in DB with matching hash.
   - **Deleted:** `source_file` in DB but file no longer on disk.
5. For new/modified files → call `RAGIngester.ingest_path()`.
6. For deleted files → delete by metadata from both chunk and parent stores.
7. Return `SyncResult`.

### 3.3 — Add `sync` subcommand to CLI

**File:** `src/tools/rag/cli.py`

```python
@rag.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--dry-run", is_flag=True, help="Report changes without applying them")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def sync(path: str, collection: str, dry_run: bool, config: str):
    """Sync a directory with a RAG collection (detect new, modified, deleted files)."""
```

Output format:

```
Syncing './vault' → collection 'notes'...

  NEW:       3 files (lecture_05.md, paper.pdf, summary.txt)
  MODIFIED:  1 file  (notes.md)
  DELETED:   1 file  (old_draft.md)
  UNCHANGED: 12 files

Sync complete: +47 chunks, -8 chunks
```

### 3.4 — Wire into `__init__.py` exports

Update `src/tools/rag/__init__.py` to export `RAGSyncer` and `SyncResult`.

---

## Phase 4: Collection Management

**Goal:** Let users browse, rename, merge, and delete collections without raw ChromaDB commands.

### 4.1 — Collection stats helper

**File:** `src/db/chroma.py` (extend `ChromaDBBackend`)

```python
def get_collection_stats(self, collection_name: str) -> dict:
    """Return doc count, chunk count, unique source files, estimated size."""
```

### 4.2 — `corpus collections` CLI group

**File:** `src/cli.py` (add command group), `src/db/collections_cli.py` (new)

Subcommands:

```
corpus collections list                    # List all collections with doc count + size
corpus collections info <name>             # Detailed stats
corpus collections rename <old> <new>      # Rename (migrate + delete old)
corpus collections merge <src...> <dest>   # Merge N collections into one
corpus collections delete <name>           # Delete with confirmation prompt
corpus collections manage                  # Launch TUI management screen
```

### 4.3 — Collection Manager TUI Screen

**File:** `src/tools/rag/tui_collections.py` (new)

A Textual `Screen` with:
- `DataTable` for collection listing (sortable columns: name, docs, chunks, size)
- Key bindings for actions (r/m/d/i/q)
- `ModalScreen` for rename input, merge source selection, delete confirmation
- Refresh after each mutation

```
┌──────────────────────────────────────────────┐
│  Collection Manager                          │
├──────────────────────────────────────────────┤
│  Name          │ Docs  │ Chunks │ Size       │
│  ────────────  │ ────  │ ────── │ ────       │
│▸ rag_notes     │   45  │  1,230 │ 12.4 MB    │
│  rag_cs101     │   12  │    340 │  3.1 MB    │
│  rag_biology   │    8  │    210 │  2.0 MB    │
├──────────────────────────────────────────────┤
│ [R]ename  [M]erge  [D]elete  [I]nfo  [Q]uit │
└──────────────────────────────────────────────┘
```

### 4.4 — Wire into TUI + slash commands

**File:** `src/tools/rag/tui.py`

Add keybinding (e.g., `ctrl+l`) to push `CollectionManagerScreen`.

Register slash commands (via Phase 2 registry):

| Command | Action |
|---------|--------|
| `/collections` | Push `CollectionManagerScreen` |
| `/collection` | Show active collection stats inline |
| `/switch <name>` | Switch active collection with toast |

---

## Phase 5: Incremental Sync Feedback in TUI

**Goal:** Make sync status visible inside the TUI. Now possible because Phase 3 provides `RAGSyncer` and `SyncResult`.

### 5.1 — Sync status bar

**File:** `src/tools/rag/tui.py`

Add a status region (sidebar footer or footer widget):

```
Last sync: 2m ago
  12 new · 3 changed · 45 unchanged
```

- On TUI mount, run a sync check (dry-run) in a background worker
- Display `SyncResult` counts in a `Static` widget
- Add keybinding (`ctrl+s`) to trigger a full sync

### 5.2 — Sync progress indicator + toast

Show a spinner during sync (via Textual `Worker`). After completion, show a `notify()` toast:

```
Sync complete: +3 new, ~1 modified, -0 deleted
```

### 5.3 — Slash commands

| Command | Action |
|---------|--------|
| `/sync` | Trigger full sync; stream progress into chat |
| `/sync status` | Render last `SyncResult` inline |
| `/sync --dry-run` | Preview changes without writing to DB |

---

## Phase 6: Export to External Formats

**Goal:** Get data *out* of CorpusRAG. Reduce lock-in anxiety.

### 6.1 — Flashcard export to Anki `.apkg`

**File:** `src/tools/flashcards/export.py` (new)

**Dependency:** `genanki` library (add to `pyproject.toml` under `[project.optional-dependencies] export`).

```python
class AnkiExporter:
    def export(self, flashcards: list[dict], deck_name: str, output_path: Path) -> Path:
        """Export flashcards to .apkg file using genanki."""
```

### 6.2 — Summary export to Markdown

**File:** `src/tools/summaries/export.py` (new)

Write summary text to `.md` with YAML frontmatter (collection, topic, timestamp, tool).

### 6.3 — Quiz export to CSV / JSON

Extend existing `QuizGenerator` with CSV and JSON export formats.

### 6.4 — CLI integration

Add `--export` / `--output` flags to `flashcards`, `summaries`, and `quizzes` CLI commands:

```bash
corpus flashcards --collection notes --export anki --output flashcards.apkg
corpus summaries --collection notes --export markdown --output summary.md
corpus quizzes --collection notes --export csv --output quiz.csv
```

### 6.5 — Bulk export command

**File:** `src/cli.py`

```bash
corpus export --collection notes --output ./export/
```

### 6.6 — Slash commands

| Command | Action |
|---------|--------|
| `/export anki` | Export flashcards to `./exports/<collection>.apkg`, toast with path |
| `/export markdown` | Export summary to `./exports/<collection>_summary.md` |
| `/export json` | Export quiz to `./exports/<collection>_quiz.json` |
| `/export` (no args) | Inline error listing valid targets |

---

## Phase 7: Model Benchmarking

**Goal:** Help users pick the best embedding model for their content.

### 7.1 — `corpus benchmark` CLI command

**File:** `src/tools/benchmark/` (new package)

```bash
corpus benchmark --collection notes --models "embeddinggemma,all-MiniLM-L6-v2,nomic-embed-text"
```

### 7.2 — Benchmark runner

**File:** `src/tools/benchmark/runner.py`

```python
@dataclass
class BenchmarkResult:
    model_name: str
    avg_retrieval_latency_ms: float
    avg_embedding_latency_ms: float
    mrr_at_10: float
    recall_at_10: float
    collection_size: int
    timestamp: str
```

**Algorithm:**

1. For each model: create temporary collection, re-embed sample documents.
2. Run eval queries (auto-generated from doc titles/headers or user-provided).
3. Measure embedding latency, retrieval latency, MRR@10, Recall@10.
4. Clean up temporary collections.
5. Print comparison table, optionally emit OpenTelemetry spans.

### 7.3 — Output format

```
Model Benchmark Results (collection: notes, 45 docs)
┌─────────────────────┬──────────┬──────────┬─────────┬────────────┐
│ Model               │ Embed ms │ Query ms │ MRR@10  │ Recall@10  │
├─────────────────────┼──────────┼──────────┼─────────┼────────────┤
│ embeddinggemma      │    12.3  │    45.2  │  0.82   │  0.91      │
│ all-MiniLM-L6-v2    │     8.1  │    32.7  │  0.78   │  0.85      │
│ nomic-embed-text    │    15.6  │    51.3  │  0.85   │  0.93      │
└─────────────────────┴──────────┴──────────┴─────────┴────────────┘
```

Also write results to `./benchmark_results.json`.

### 7.4 — Slash commands

| Command | Action |
|---------|--------|
| `/benchmark` | Run benchmark on active collection with default models; stream results |
| `/benchmark <model1> <model2>` | Compare specific models |

---

## Phase 8: README + Documentation

**Goal:** Update all documentation to reflect new features and fix stale references.

### 8.1 — Fix stale CorpusCallosum references

- Line 68: `git clone` URL → `CorpusRAG`
- Line 69: `cd CorpusCallosum` → `cd CorpusRAG`
- Line 263: `CC_LLM_MODEL` env var prefix → `CORPUSRAG_LLM_MODEL`
- Line 311: Project structure tree → `CorpusRAG/`

### 8.2 — Replace Black/isort references with Ruff

Update code quality section to reference `ruff format` and `ruff check` instead of `black` and `isort`.

### 8.3 — Document new commands

- `corpus rag sync` (with `--dry-run`)
- `corpus collections` subcommands (list, info, rename, merge, delete, manage)
- `corpus export` (bulk export)
- `corpus benchmark`
- Slash command system (`/help` for full list)
- Export flags on flashcards/summaries/quizzes

### 8.4 — Update feature highlights

Add bullets for: Vault Sync, Collection Manager, Export, Slash Commands, Benchmarking.

---

## Phase 9: Verification

### 9.1 — Local verification

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pytest tests/ -v --ignore=tests/test_smoke.py
```

### 9.2 — CI simulation with `act`

Run `act` to simulate the GitHub Actions environment locally. Fix any failures.

### 9.3 — Commit strategy

| Commit | Content |
|--------|---------|
| 1 | Fix ruff lint errors and format files (Phase 1) |
| 2 | Add TUI slash command router (Phase 2) |
| 3 | Add `corpus rag sync` command with RAGSyncer (Phase 3) |
| 4 | Add collection management CLI and TUI (Phase 4) |
| 5 | Add sync feedback in TUI (Phase 5) |
| 6 | Add export to Anki/Markdown/CSV/JSON (Phase 6) |
| 7 | Add model benchmarking command (Phase 7) |
| 8 | Update README and documentation (Phase 8) |

---

## Dependency Graph

```
Phase 1 (CI fixes)
    ↓
Phase 2 (slash command router)
    ↓
Phase 3 (RAGSyncer + sync CLI)
    ↓
    ├── Phase 4 (collection management) ← uses slash commands from Phase 2
    │       ↓
    ├── Phase 5 (sync TUI feedback) ← uses RAGSyncer from Phase 3 + slash commands from Phase 2
    │
    ├── Phase 6 (export) ← uses slash commands from Phase 2
    │
    └── Phase 7 (benchmarking) ← uses slash commands from Phase 2
            ↓
        Phase 8 (README) ← documents everything above
            ↓
        Phase 9 (verification)
```

Phases 4, 6, and 7 are independent of each other and could theoretically be parallelized, but sequential implementation is recommended for clean commits.

---

## New Dependencies

| Package | Phase | Optional? |
|---------|-------|-----------|
| `genanki` | Phase 6 (Anki export) | Yes — under `[export]` extra |

---

## File Change Summary

| File | Phase | Action |
|------|-------|--------|
| `src/mcp_server/server.py` | 1 | Add `SecurityError` import |
| `pyproject.toml` | 1, 6 | Add per-file-ignore; add `genanki` to `[export]` deps |
| ~40 files (src/ + tests/) | 1 | `ruff format` whitespace fixes |
| `src/tools/rag/slash_commands.py` | 2 | **NEW** — router, registry, result types, `/help`, `/clear`, `/ask` |
| `src/tools/rag/tui.py` | 2, 4, 5 | Wire slash interception; collection keybinding; sync status bar |
| `src/tools/rag/ingest.py` | 3 | Add `source_file_name` metadata field |
| `src/tools/rag/sync.py` | 3 | **NEW** — `RAGSyncer` class, `SyncResult` dataclass |
| `src/tools/rag/cli.py` | 3 | Add `sync` subcommand |
| `src/tools/rag/__init__.py` | 3 | Export `RAGSyncer`, `SyncResult` |
| `src/db/chroma.py` | 4 | Add `get_collection_stats()` method |
| `src/db/collections_cli.py` | 4 | **NEW** — collection management CLI |
| `src/cli.py` | 4, 6 | Add `collections` and `export` command groups |
| `src/tools/rag/tui_collections.py` | 4 | **NEW** — Collection Manager TUI screen; `/collections`, `/collection`, `/switch` |
| `src/tools/flashcards/export.py` | 6 | **NEW** — Anki `.apkg` exporter; `/export anki` |
| `src/tools/summaries/export.py` | 6 | **NEW** — Markdown exporter; `/export markdown` |
| `src/tools/flashcards/cli.py` | 6 | Add `--export` / `--output` flags |
| `src/tools/summaries/cli.py` | 6 | Add `--export` / `--output` flags |
| `src/tools/quizzes/cli.py` | 6 | Add `--export` / `--output` flags; `/export json` |
| `src/tools/benchmark/` | 7 | **NEW** — benchmark package (runner, cli, __init__); `/benchmark` |
| `README.md` | 8 | Fix stale refs, document all new commands |

---

## Risks & Notes

- **`ruff format` on ~40 files** produces a large diff. Commit separately (Phase 1) for clean git history.
- **`source_file_name` metadata** is additive — existing collections won't have it on old chunks. Sync logic falls back to `source_file` for matching.
- **Deleted file detection** requires querying all unique `source_file` values. ChromaDB's `get` with `include=["metadatas"]` handles typical vault sizes (< 10k files).
- **`genanki` is optional** — export features degrade gracefully if not installed.
- **mypy** is in CI — address any type errors that surface during Phase 9 verification.
