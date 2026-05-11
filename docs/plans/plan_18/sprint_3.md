# Sprint 3 — Backup Consolidation, Doctor Promotion, TUI Exit Fix

**Plan:** docs/plans/plan_18/OVERVIEW.md
**Wave:** 3 of 6
**Can run in parallel with:** none — depends on Sprint 2
**Must complete before:** Sprint 4

---

## Agents in This Wave

### Agent A: C7 — Consolidate `db backup-all` into `db backup --all`

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/db/management.py` — remove `backup-all` command, add `--all` flag to `backup`

**Depends on:** C6
**Blocks:** C8 (same file)

**Instructions:**
Delete the `backup_all_cmd` Click command. Modify the existing `backup_cmd` to accept an `--all` flag. When `--all` is passed:
- The `collection` argument becomes optional (use `click.Argument` with `required=False` or handle via callback)
- The `--output` path is treated as a directory (not a file)
- Call `manager.backup_all_collections(output, ...)` instead of `manager.backup_collection(...)`

When `--all` is NOT passed, `collection` is required and behavior is unchanged.

**Definition of Done:**
- [ ] `corpus db backup --all -o ./backups/` backs up all collections
- [ ] `corpus db backup my_collection -o backup.tar.gz` still works
- [ ] `corpus db backup-all` returns "No such command"
- [ ] No regressions in existing tests

---

### Agent B: C9 — Move `doctor` to Top-Level CLI

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/cli.py` — register `doctor` as a top-level command
- `src/tools/rag/cli.py` — remove or hide the `doctor` command from the `rag` group
- `src/tools/rag/doctor.py` — ensure it can run without RAG-specific config (check all services)

**Depends on:** C1 (cli.py modified), C10 (rag/cli.py modified)
**Blocks:** none

**Instructions:**
In `src/cli.py`, add a new top-level `doctor` command (not lazy-loaded since it's lightweight). It should import and call `run_doctor` from `src/tools/rag/doctor.py`. In `src/tools/rag/cli.py`, remove the `doctor` command registration (or mark it as `hidden=True` for backward compat). The doctor function itself may need a small refactor to accept a base config rather than requiring RAGConfig specifically — check if it only uses `database` and `llm` sections.

**Definition of Done:**
- [ ] `corpus doctor` runs health checks and prints results
- [ ] `corpus rag doctor` either still works (hidden) or returns helpful error
- [ ] Doctor checks db connectivity, LLM endpoint, and embedding service
- [ ] No regressions in existing tests

---

### Agent C: C12 — Fix TUI Exit Terminal Corruption

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/rag/tui.py` — fix terminal state restoration on exit
- `src/tools/rag/tui_collections.py` — same fix for collections TUI

**Depends on:** C11 (tui.py keybindings done), C3 (tui_collections.py cleaned)
**Blocks:** C14

**Instructions:**
The TUI (Textual app) is not properly restoring terminal state on exit. Investigate:
1. Is `app.run()` being called correctly? Textual should handle cleanup automatically.
2. Check if there's a custom `on_unmount` or signal handler that's interfering.
3. Look for raw terminal manipulation (e.g., direct ANSI escape sequences) that bypasses Textual's lifecycle.
4. Ensure the `quit` action calls `self.exit()` (not `sys.exit()` or `raise SystemExit`).
5. For the collections TUI (`CollectionManagerApp`), ensure the same pattern.

On Windows, also check that the console mode is being restored. Textual's `App.run()` should handle this, but custom code may be breaking it.

**Definition of Done:**
- [ ] After `corpus rag ui` exits, terminal input/output works normally
- [ ] After `corpus collections manage` exits, terminal works normally
- [ ] Tested on Windows Terminal
- [ ] No raw escape sequences left in terminal after exit
- [ ] No regressions in existing tests
