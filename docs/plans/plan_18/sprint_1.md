# Sprint 1 — Foundation: CLI Group, Dead Code Removal, DB Logging, TUI Keybindings

**Plan:** docs/plans/plan_18/OVERVIEW.md
**Wave:** 1 of 6
**Can run in parallel with:** none — this is the first wave
**Must complete before:** Sprint 2

---

## Agents in This Wave

### Agent A: C1 — CLI Hierarchy Restructure: Create `corpus tools` Group

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/cli.py` — rewire lazy_subcommands to nest under tools group
- `src/tools/__init__.py` (NEW) — package init
- `src/tools/cli.py` (NEW) — define the `tools` Click group with subcommands

**Depends on:** none
**Blocks:** C2, C9

**Instructions:**
Create `src/tools/cli.py` with a Click group named `tools` that registers `rag`, `video`, `handwriting`, and `summaries` as lazy subcommands (same pattern as the root `cli.py`). In `src/cli.py`, replace the existing flat lazy_subcommands with just `"tools": "tools.cli:tools"`, `"db": "db.management:db"`, `"collections": "db.collections_cli:collections_cmd"`, and `"dev": "cli_dev:dev"`. Remove all old top-level tool aliases (`rag`, `video`, `flashcards`, `handwriting`, `summaries`, `quizzes`, `orchestrate`). The `tools` group should also register a `learning` subgroup (placeholder for C2).

**Definition of Done:**
- [ ] `corpus tools rag --help` works
- [ ] `corpus tools video --help` works
- [ ] `corpus rag` returns "No such command" (old alias removed)
- [ ] `src/tools/__init__.py` exists with empty or minimal content
- [ ] No regressions in existing tests

---

### Agent B: C3 — Remove Dead Commands: `collections merge` and `collections rename`

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/db/collections_cli.py` — delete `merge_collections` and `rename_collection` functions and their `@collections_cmd.command` decorators
- `src/tools/rag/tui_collections.py` — remove any buttons, actions, or menu items referencing merge/rename

**Depends on:** none
**Blocks:** C4 (same file)

**Instructions:**
Open `src/db/collections_cli.py` and delete the `merge` and `rename` commands entirely (both the Click command functions and any helper logic). In `src/tools/rag/tui_collections.py`, search for any references to merge or rename operations and remove them (buttons, action handlers, menu entries). Run existing tests to confirm nothing depends on these commands.

**Definition of Done:**
- [ ] `corpus collections merge` returns "No such command"
- [ ] `corpus collections rename` returns "No such command"
- [ ] TUI collections manager has no merge/rename options
- [ ] `tests/test_collections_cli.py` passes (update if it tests merge/rename)
- [ ] No regressions in existing tests

---

### Agent C: C5 — Suppress HTTP Request Logging in DB Commands

**Complexity:** S
**Estimated time:** 30 minutes
**Files to modify:**
- `src/db/management.py` — add logging suppression in the `db` group callback

**Depends on:** none
**Blocks:** C6, C7, C8 (same file)

**Instructions:**
In the `db()` Click group function (the `@click.group()` callback), add these lines before or after the existing `logging.basicConfig` call:

```python
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb.telemetry").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
```

This suppresses the HTTP request noise that clutters the terminal when running `db list`, `db backup`, `db export`, etc.

**Definition of Done:**
- [ ] `corpus db list` shows only collection info, no HTTP request lines
- [ ] `corpus db backup` output is clean
- [ ] `corpus db export` output is clean
- [ ] No regressions in existing tests

---

### Agent D: C11 — Change TUI Keybindings Off F1-F5

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/rag/tui.py` — replace F1-F5 bindings with Ctrl/Alt alternatives

**Depends on:** none
**Blocks:** C10, C12, C14 (same file, later waves)

**Instructions:**
In `src/tools/rag/tui.py`, find all `Binding` definitions that use `f1` through `f5`. Replace them with non-conflicting alternatives. Suggested mapping:
- F1 (help) → `ctrl+h` or `ctrl+?`
- F2 (context) → `ctrl+x`
- F3 (collections) → `ctrl+o`
- F4 (settings) → `ctrl+s` (if not used) or `ctrl+,`
- F5 (quit) → `ctrl+q`

Update the footer/help text to reflect the new bindings. Ensure the bindings don't conflict with Textual's built-in bindings or common terminal sequences.

**Definition of Done:**
- [ ] No F1-F5 bindings remain in tui.py
- [ ] New keybindings are documented in the TUI help panel
- [ ] TUI launches and responds to new keybindings correctly
- [ ] No regressions in existing tests
