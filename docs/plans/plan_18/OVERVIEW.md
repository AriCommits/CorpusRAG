# Plan 18: CLI Restructure, Dead Feature Removal & DB Serialization Fixes

## Summary

Restructure the CorpusRAG CLI hierarchy to consolidate tools under a `corpus tools` namespace, group learning-related commands (flashcards, quizzes) under `corpus tools learning`, remove broken/dead commands (`collections merge`, `collections rename`), fix the `collections info` CLI path, fix TUI exit/terminal corruption issues, suppress HTTP request noise in `db` commands, fix `ndarray` JSON serialization bugs in backup/export, move `doctor` to the top-level CLI, make `rag ui --collection` optional, and add documentation scaffolding instructions for coding agents across all touched files.

## Goals

- Consolidate `rag`, `video`, `handwriting`, `summaries`, `flashcards`, `quizzes` under `corpus tools <tool>`
- Group `flashcards` and `quizzes` under `corpus tools learning`
- Remove dead commands: `collections merge`, `collections rename`
- Remove merge/rename access from the TUI collections manager
- Fix `collections info` so it works from CLI (not just TUI)
- Fix TUI exit leaving terminal in broken state
- Suppress HTTP request logging noise in `db list`, `db backup`, `db export`
- Fix `ndarray` not JSON-serializable error in `db backup-all` and `db export`
- Consolidate `db backup-all` into `db backup --all` flag
- Consolidate `db export` with `db backup` or clarify distinction; embeddings included by default in export
- Store embedding model name in export metadata for portability
- Move `corpus rag doctor` to `corpus doctor`
- Make `corpus rag ui` collection argument optional; allow selection from within TUI
- Change TUI keybindings off F1-F5 to avoid IDE conflicts
- Store ingest path in collection metadata so `rag sync` can default to it
- Add `collections update-path` command
- Every modified file must include/update module-level docstring scaffolding for documentation

## Non-Goals

- Rewriting the RAG pipeline internals
- Changing the MCP server
- Adding new tools or generators
- Modifying the embedding or LLM backends
- Changing the database schema beyond metadata additions

## Background / Context

- Plan 17 addressed lazy CLI loading; this plan builds on that foundation
- The CLI currently uses a flat namespace (`corpus rag`, `corpus video`, `corpus flashcards`, etc.)
- ChromaDB returns embeddings as numpy `ndarray` which `json.dump` cannot serialize
- The TUI uses Textual and has terminal restoration issues on exit
- HTTP logging from `httpx`/`chromadb` client leaks into CLI output

## Features / Tasks

### C1: CLI Hierarchy Restructure — Create `corpus tools` Group
**Files:** `src/cli.py` (modify), `src/tools/__init__.py` (new), `src/tools/cli.py` (new)
**Complexity:** M
**Depends on:** none

Create a new `tools` Click group that nests: `rag`, `video`, `handwriting`, `summaries`, and a new `learning` subgroup. Remove the old top-level aliases (`corpus rag`, `corpus video`, `corpus flashcards`, etc.) entirely — no backward compat needed. Update `cli.py` lazy_subcommands mapping to only have `tools`, `db`, `collections`, `dev`.

### C2: Create `corpus tools learning` Subgroup
**Files:** `src/tools/learning/__init__.py` (new), `src/tools/learning/cli.py` (new), `src/tools/flashcards/cli.py` (modify), `src/tools/quizzes/cli.py` (modify)
**Complexity:** S
**Depends on:** C1

Create `src/tools/learning/cli.py` with a Click group named `learning` that lazily loads `flashcards` and `quizzes` subcommands. Register this group in the `tools` group created in C1. The individual tool CLIs remain unchanged internally; only the registration path changes.

### C3: Remove Dead Commands — `collections merge` and `collections rename`
**Files:** `src/db/collections_cli.py` (modify), `src/tools/rag/tui_collections.py` (modify)
**Complexity:** S
**Depends on:** none

Delete the `merge_collections` and `rename_collection` CLI commands. Remove any TUI buttons/actions that reference merge or rename in the collections management screen.

### C4: Fix `collections info` CLI Path
**Files:** `src/db/collections_cli.py` (modify)
**Complexity:** S
**Depends on:** none

The `info` command works from TUI but fails from CLI. Debug and fix — likely a config loading or db connection issue when invoked standalone. Ensure `corpus collections info <name>` works end-to-end.

### C5: Suppress HTTP Request Logging in DB Commands
**Files:** `src/db/management.py` (modify)
**Complexity:** S
**Depends on:** none

Add `logging.getLogger("httpx").setLevel(logging.WARNING)` and `logging.getLogger("chromadb").setLevel(logging.WARNING)` at the top of the `db` group callback so HTTP noise is suppressed for all db subcommands.

### C6: Fix ndarray JSON Serialization in Backup/Export
**Files:** `src/db/management.py` (modify)
**Complexity:** M
**Depends on:** none

Add a custom JSON encoder (or pre-conversion step) that converts `numpy.ndarray` to Python lists before serialization. Apply to both `backup_collection` and `export_collection`. Embeddings should be included by default in export (flip the default for `--include-embeddings`).

### C7: Consolidate `db backup-all` into `db backup --all`
**Files:** `src/db/management.py` (modify)
**Complexity:** S
**Depends on:** C6

Remove the `backup-all` command. Add an `--all` flag to the existing `backup` command. When `--all` is passed, ignore the collection argument and back up everything to the output directory.

### C8: Store Embedding Model in Export Metadata
**Files:** `src/db/management.py` (modify), `src/tools/rag/ingest.py` (modify)
**Complexity:** S
**Depends on:** C6

When exporting, include `embedding_model` in the export JSON metadata (read from config). When ingesting, store the embedding model name in ChromaDB collection metadata so exports are self-contained.

### C9: Move `doctor` to Top-Level CLI
**Files:** `src/cli.py` (modify), `src/tools/rag/cli.py` (modify), `src/tools/rag/doctor.py` (modify)
**Complexity:** S
**Depends on:** C1

Register `doctor` as `corpus doctor` at the top level. Remove it from the `rag` subgroup (or keep as hidden alias). The doctor command should check all configured services (db, llm, embedding).

### C10: Make `rag ui --collection` Optional + In-TUI Collection Selection
**Files:** `src/tools/rag/cli.py` (modify), `src/tools/rag/tui.py` (modify)
**Complexity:** M
**Depends on:** none

Change `--collection` from required to optional. If omitted, the TUI should present a collection picker on startup. Add a way to switch collections from within the TUI (e.g., a slash command `/collection <name>` or a panel).

### C11: Change TUI Keybindings Off F1-F5
**Files:** `src/tools/rag/tui.py` (modify)
**Complexity:** S
**Depends on:** none

Replace F1-F5 bindings with Ctrl-based or Alt-based shortcuts that don't conflict with IDE integrated terminals. Document the new bindings in the TUI help panel.

### C12: Fix TUI Exit Terminal Corruption
**Files:** `src/tools/rag/tui.py` (modify), `src/tools/rag/tui_collections.py` (modify)
**Complexity:** M
**Depends on:** none

Investigate and fix the terminal state not being restored after TUI exit. Ensure `app.run()` properly calls shutdown hooks and the alternate screen buffer is released. Test on Windows Terminal and common Linux terminals.

### C13: Store Ingest Path in Collection Metadata + `sync` Default Path
**Files:** `src/tools/rag/ingest.py` (modify), `src/tools/rag/cli.py` (modify), `src/db/collections_cli.py` (modify)
**Complexity:** M
**Depends on:** none

When `corpus rag ingest <path> -c <name>` runs, store the resolved path in collection metadata (`ingest_source_path`). When `corpus rag sync -c <name>` is called without a path argument, read the stored path from metadata. Add `corpus collections update-path <collection> <new-path>` command.

### C14: Add Collections Management to RAG TUI
**Files:** `src/tools/rag/tui.py` (modify)
**Complexity:** S
**Depends on:** C10, C12

Add a way to access the collections management screen from within the RAG TUI (e.g., via slash command `/collections` or a keybinding), so users don't need to exit and re-enter via `corpus collections manage`.

### D1: Documentation Scaffolding Across All Touched Files
**Files:** all files listed above (modify)
**Complexity:** S
**Depends on:** C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14

Every file modified or created in this plan must have:
- A module-level docstring explaining purpose, public API, and usage
- Inline `# TODO(plan_18):` comments where behavior changed
- Updated `src/CLI.md` reflecting the new command hierarchy

**Coding Agent Instructions:** When implementing any task above, begin by reading the target file's existing docstring. If none exists, add one following this template:
```python
"""<Module title>.

<One-paragraph description of what this module does.>

Public API:
    - <function/class>: <brief description>

CLI Commands (if applicable):
    - <command path>: <brief description>

See Also:
    - docs/plans/plan_18/OVERVIEW.md
"""
```
Update `src/CLI.md` to reflect any command additions, removals, or path changes made in your task.

## New Dependencies

| Package | Feature | Optional? |
|---------|---------|-----------|
| (none)  | —       | —         |

No new dependencies required. The `numpy` ndarray fix uses numpy's `.tolist()` method which is already available since numpy is a transitive dependency of chromadb.

## File Change Summary

| File | Action |
|------|--------|
| `src/cli.py` | modify |
| `src/tools/__init__.py` | new |
| `src/tools/cli.py` | new |
| `src/tools/learning/__init__.py` | new |
| `src/tools/learning/cli.py` | new |
| `src/tools/flashcards/cli.py` | modify |
| `src/tools/quizzes/cli.py` | modify |
| `src/db/collections_cli.py` | modify |
| `src/db/management.py` | modify |
| `src/tools/rag/cli.py` | modify |
| `src/tools/rag/tui.py` | modify |
| `src/tools/rag/tui_collections.py` | modify |
| `src/tools/rag/doctor.py` | modify |
| `src/tools/rag/ingest.py` | modify |
| `src/CLI.md` | modify |

## Open Questions

1. Should `db export` and `db backup` be fully merged into a single `db copy` command, or remain separate with clearer naming?
2. What keybinding scheme for the TUI? Proposal: Ctrl+1 through Ctrl+5, or Ctrl+Shift+<letter> combos.
