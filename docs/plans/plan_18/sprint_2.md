# Sprint 2 — Learning Group, Collections Fix, DB Serialization, TUI Optional Collection

**Plan:** docs/plans/plan_18/OVERVIEW.md
**Wave:** 2 of 6
**Can run in parallel with:** none — depends on Sprint 1
**Must complete before:** Sprint 3

---

## Agents in This Wave

### Agent A: C2 — Create `corpus tools learning` Subgroup

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/learning/__init__.py` (NEW) — package init
- `src/tools/learning/cli.py` (NEW) — define `learning` Click group registering flashcards and quizzes
- `src/tools/flashcards/cli.py` — no internal changes, just ensure it's importable as a subcommand
- `src/tools/quizzes/cli.py` — same as above

**Depends on:** C1
**Blocks:** none

**Instructions:**
Create `src/tools/learning/cli.py` with a Click group named `learning` that lazily loads `flashcards` and `quizzes` subcommands. Register this group in the `tools` group created in C1 (modify `src/tools/cli.py` to add `"learning": "tools.learning.cli:learning"`). The flashcards and quizzes CLIs don't need internal changes — they're already self-contained Click groups.

**Definition of Done:**
- [ ] `corpus tools learning flashcards --help` works
- [ ] `corpus tools learning quizzes --help` works
- [ ] No regressions in existing tests

---

### Agent B: C4 — Fix `collections info` CLI Path

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/db/collections_cli.py` — debug and fix the `info` command for standalone CLI invocation

**Depends on:** C3 (same file, now clean)
**Blocks:** C13 (same file)

**Instructions:**
The `collections info` command works from the TUI but fails from CLI. The likely issue is that `load_cli_db` is being called with `BaseConfig` which may not initialize the ChromaDB connection properly in all modes. Debug by running `corpus collections info <collection_name>` and tracing the error. Ensure the config loading path and db connection work identically whether invoked from TUI or CLI. Check that the `get_collection_stats` method handles both persistent and HTTP mode connections.

**Definition of Done:**
- [ ] `corpus collections info <name>` returns stats table without error
- [ ] Works in both persistent and HTTP ChromaDB modes
- [ ] No regressions in existing tests

---

### Agent C: C6 — Fix ndarray JSON Serialization in Backup/Export

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/db/management.py` — add ndarray-safe serialization, flip export embeddings default

**Depends on:** C5 (same file, logging fix applied)
**Blocks:** C7, C8

**Instructions:**
Add a custom JSON encoder class or a pre-serialization helper:

```python
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)
```

Use `cls=NumpyEncoder` in all `json.dump` calls within `backup_collection`, `backup_all_collections`, and `export_collection`. Also change `export_collection`'s `include_embeddings` parameter default from `False` to `True`. Update the CLI `--include-embeddings` flag to `--no-embeddings` (inverted logic) so embeddings are included by default.

**Definition of Done:**
- [ ] `corpus db backup <collection> -o backup.tar.gz` succeeds without ndarray error
- [ ] `corpus db export <collection> -o export.json` includes embeddings by default
- [ ] `corpus db export <collection> -o export.json --no-embeddings` excludes them
- [ ] Backup/export files contain valid JSON with embedding arrays as lists
- [ ] No regressions in existing tests

---

### Agent D: C10 — Make `rag ui --collection` Optional + In-TUI Collection Selection

**Complexity:** M
**Estimated time:** 2.5 hours
**Files to modify:**
- `src/tools/rag/cli.py` — change `--collection` from required to optional
- `src/tools/rag/tui.py` — add collection picker screen when no collection specified; add `/collection` slash command

**Depends on:** C11 (tui.py keybindings updated)
**Blocks:** C14, C9 (rag/cli.py)

**Instructions:**
In `src/tools/rag/cli.py`, change the `ui` command's `--collection` option to `required=False, default=None`. In `src/tools/rag/tui.py`, if `collection` is None on startup, show a collection picker modal/screen that lists available collections (use `db.list_collections()`). Add a `/collection <name>` slash command that switches the active collection mid-session. The RAGApp class will need to accept `collection=None` and handle the picker flow.

**Definition of Done:**
- [ ] `corpus rag ui` launches without error (no --collection required)
- [ ] Collection picker appears when no collection specified
- [ ] `/collection <name>` switches active collection in TUI
- [ ] `corpus rag ui -c notes` still works as before
- [ ] No regressions in existing tests
