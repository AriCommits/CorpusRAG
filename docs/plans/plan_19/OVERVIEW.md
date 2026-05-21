# Plan 19: Update Pytest Suite for Plan 18 CLI Restructure

## Summary

Update the test suite to reflect the CLI restructure from Plan 18. The main CLI now uses `corpus tools <tool>` instead of flat `corpus <tool>` commands. Tests referencing old command paths, removed commands (merge/rename), and the old `--skip-augment` flag need updating.

## Goals

- All existing tests pass against the new CLI structure
- Tests verify the new `corpus tools` hierarchy works
- Tests verify removed commands (merge, rename, backup-all) are gone
- Tests verify new features (doctor at top-level, optional collection in ui, --augment flag)

## Features / Tasks

### T1: Update `tests/unit/test_cli.py` — Fix CLI hierarchy tests
**Files:** `tests/unit/test_cli.py` (modify)
**Complexity:** M
**Depends on:** none

The `TestCorpusGroup.test_help_lists_all_subcommands` test checks for old flat commands (`rag`, `video`, `orchestrate`, `flashcards`, `handwriting`, `summaries`, `quizzes`). These are now under `tools`. Update to check for `tools`, `db`, `collections`, `dev`, `setup`, `benchmark`, `doctor`. Also update `test_rag_subgroup_reachable`, `test_video_subgroup_reachable`, `test_orchestrate_subgroup_reachable`, `test_flashcards_reachable`, `test_handwriting_subgroup_reachable`, `test_summaries_reachable`, `test_quizzes_reachable` to use `corpus tools <tool>` paths.

### T2: Update `tests/unit/test_video_cli.py` — Fix pipeline test
**Files:** `tests/unit/test_video_cli.py` (modify)
**Complexity:** S
**Depends on:** none

Add test for `pipeline --help` verifying `--augment` flag exists (not `--skip-augment`). Verify `pipeline` help text is accessible.

### T3: Update `tests/test_collections_cli.py` — Remove merge/rename test expectations
**Files:** `tests/test_collections_cli.py` (modify)
**Complexity:** S
**Depends on:** none

Add tests verifying `merge` and `rename` commands no longer exist. Verify `update-path` command exists.

## File Change Summary

| File | Action |
|------|--------|
| `tests/unit/test_cli.py` | modify |
| `tests/unit/test_video_cli.py` | modify |
| `tests/test_collections_cli.py` | modify |

## Open Questions

None.
