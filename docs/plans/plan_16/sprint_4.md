# Sprint 4 — CLI Integration

**Plan:** docs/plans/plan_16/handwriting_ingest_spec.md
**Wave:** 4 of 4
**Can run in parallel with:** none — single agent
**Must complete before:** end of plan

---

## Agents in This Wave

### Agent H: H7 — Click CLI + Wire-Up

**Complexity:** S
**Estimated time:** 1.5 h
**Files to modify:**
- `src/tools/handwriting/cli.py` (NEW) — `handwriting` Click group + `ingest` command per spec §Step 8.
- `src/cli.py` — add `from src.tools.handwriting.cli import handwriting` and `cli.add_command(handwriting)`.
- `tests/tools/handwriting/test_cli.py` (NEW) — Click `CliRunner` invocation with mocked `Agent` and `ingest_handwriting`.

**Depends on:** H6
**Blocks:** none

**Instructions:**

Implement `tools/handwriting/cli.py` per spec §Step 8. Notes:

1. **All flags from the spec**: `--collection/-c`, `--recursive/--no-recursive`, `--vision-model`, `--correction-model`, `--no-autocorrect`, `--tags/-t` (multiple), `--context-window`, `--keep-preprocessed`.

2. **Add `--max-depth` flag** (per spec Open Question #5): integer, default `None`, passed through to `walk_directory`. Note this means the orchestrator from Sprint 3 must accept and forward `max_depth` — verify Sprint 3's `ingest_handwriting` signature includes it; if Sprint 3 omitted it, add the parameter to the orchestrator as part of this sprint.

3. **Output formatting**: keep the `click.echo` summary format from the spec (Total / Already ingested / Blank / Pages ingested / Low confidence). If `result.failed_pages > 0`, emit an additional warning line. If `result.warnings_file`, print its path so the user can find it.

4. **Wire-up**: open `src/cli.py`, find the existing `cli.add_command(...)` calls, and add the handwriting group alongside them. Match the import style of sibling tool registrations.

5. **Tests**: use `click.testing.CliRunner`. Patch `src.tools.handwriting.cli.Agent` and `src.tools.handwriting.cli.ingest_handwriting` so the test doesn't need ChromaDB or Ollama. Verify:
   - `corpus handwriting --help` lists the `ingest` command.
   - `corpus handwriting ingest <tmp_dir> --collection foo` calls `ingest_handwriting` with `collection="foo"`.
   - Repeated `--tags` flags accumulate into a list.
   - `--no-recursive` flips the `recursive` kwarg.

**Definition of Done:**
- [ ] `corpus handwriting ingest --help` shows all documented flags.
- [ ] CLI invocation calls `ingest_handwriting` with correctly mapped kwargs.
- [ ] `--no-autocorrect` toggles `autocorrect=False` (the flag is inverted).
- [ ] `--keep-preprocessed` toggles `cleanup_preprocessed=False`.
- [ ] Multiple `-t` flags become `user_tags=["a", "b"]`.
- [ ] `cli.add_command(handwriting)` registered in main `cli.py`.
- [ ] `corpus --help` shows `handwriting` group at the top level.
- [ ] All tests pass; no regressions in existing CLI tests.
