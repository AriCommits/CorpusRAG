# Sprint 3 — Verification, Formatting, and Consistency

**Plan:** docs/plans/plan_20/OVERVIEW.md
**Wave:** 3 of 3
**Can run in parallel with:** none — serial (single integration agent)
**Must complete before:** merge to main / release
**Prerequisites:** Sprints 1 and 2 fully merged (C1, C2, O1, O2, D1, D2, P1 complete).

---

## Agents in This Wave

### Agent A: V1 — Verification, formatting, and consistency tests

**Complexity:** M
**Estimated time:** 2–3 hours
**Files to modify:**
- `tests/test_cli_docs_consistency.py` (NEW)
- Repo-wide formatting sweep (`ruff format` may touch any `src/`/`tests/` file that drifted).

**Depends on:** C1, C2, O1, O2, D1, D2, P1
**Blocks:** none (final gate)

**Instructions:**
This is the integration/verification pass after all build tasks land.

1. **CLI ↔ docs consistency tests** — build the "command tree" as the set of full command paths
   reachable from the root `corpus` Click group (walk `group.commands` recursively, resolving
   `LazyGroup` lazy subcommands). Then:
   - `# Feature: project-hardening, Property 1: cli.txt matches the live command tree exactly` —
     assert the top-level command set parsed from `cli.txt` equals the reachable top-level command
     set (no missing, no extra), including `doctor`, `tools`, and `orchestrate`.
   - `# Feature: project-hardening, Property 2: every documented command example resolves to a real
     command` — extract fenced `corpus ...` examples from `README.md` and `src/CLI.md`; assert each
     resolves against the live tree; on failure, report the source document and offending command.
   These iterate the full command set / all extracted examples, so implement them as
   enumerated/parametrized tests (they express a universal invariant without random input).

2. **Formatting** — run `ruff format src/ tests/` so `ruff format --check` reports zero diffs. Run
   `ruff check src/ tests/` and fix any lint fallout from the wave edits.

3. **Full-suite + CI dry run** — run `pytest` locally (respecting the `-m 'not live'` default), then
   verify the CI-critical commands succeed: `uv lock --check`, `uv run ruff check`,
   `uv run ruff format --check`, `uv run deptry src`. Confirm the pytest matrix passes with a copied
   `configs/base.yaml`.

4. **Cross-cutting doc assertions** (grep-style, may live in this test file): zero flat `corpus rag`
   outside a migration note; zero legacy-name occurrences outside a migration note; zero
   `KnowledgeBaseOrchestrator`/`study-session` refs outside a removal note; zero `corpus-config`/
   `corpus-secrets`/`corpus_callosum.config.base`/`CORPUSRAG_CONFIG`.

**Definition of Done:**
- [ ] `cli.txt` set-equals the live command tree (Property 1) and all doc examples resolve
      (Property 2); both tests pass.
- [ ] `ruff format --check` reports zero files needing reformatting; `ruff check` clean.
- [ ] `uv lock --check`, `deptry`, and the full pytest suite pass locally.
- [ ] Cross-cutting doc/grep assertions pass.
- [ ] All CI jobs (lint, test 3.11/3.12, docker-build) green.
- [ ] No regressions in existing tests.
