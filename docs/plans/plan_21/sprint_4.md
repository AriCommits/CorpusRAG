# Sprint 4 — Verify, Format, Consistency

**Plan:** docs/plans/plan_21/OVERVIEW.md
**Wave:** 4 of 4
**Can run in parallel with:** none — serial, last wave
**Must complete before:** nothing (closes the plan)

Branch from post-Wave-3 `main`.

---

## Agents in This Wave

### Agent A: V1 — Verify, format, leftover bytecode, consistency tests

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- Any file `ruff format` rewrites under `src/` and `tests/`.
- `tests/test_dead_code_removal.py` — assert D1/D3 deletes still gone.
- `tests/test_cli_docs_consistency.py` — only if a cheap assertion belongs
  here (live Click tree vs README/`src/CLI.md`; do not scrape all of
  `docs/architecture.md` unless already patterned).
- Leftover `src/orchestrations/__pycache__/study_session*.pyc` and
  `knowledge_base*.pyc` on disk (gitignored; delete locally so they stop
  confusing greps). Do not commit pycache.

**Depends on:** DOC1, S1, S2, S4, D3
**Blocks:** none

**Instructions:**
This is an integration pass, not a feature pass.

1. `uv run ruff format src tests`
2. `uv run ruff check src tests`
3. `uv run deptry src`
4. `uv lock --check`
5. `uv run pytest tests/ -m "not live"`

Confirm by grep that these are gone from `src/`:
- `LangChainVectorStoreAdapter`
- `SecretManager` / `utils.secrets` / `utils.tokens`
- `tools.rag.message` / `tools.rag.context`
- `from_dict(config.to_dict())` in `mcp_server/` without `raw or`
- `VideoTranscriber(self.video_config, self.db)`
- `summary.text` in summaries CLI
- `corpus rag ui` in `src/` (must be `corpus tools rag ui`)
- quiz/flashcard placeholder padding (`Additional Question`)

If any of those still exist, fix them in this wave only if they are
one-line fallout from format/merge; otherwise open a follow-up rather
than restating S1–S4. Prefer fixing if the test suite already fails.

Extend `tests/test_dead_code_removal.py` so a reintroduced shim/adapter/
secrets module fails CI.

Do not add features, do not rewrite docs (DOC1 is done), do not touch
`docs/plans/` except if ruff somehow would (it will not).

**Definition of Done:**
- [ ] `ruff format --check src tests` clean.
- [ ] `ruff check src tests` clean.
- [ ] `deptry src` clean.
- [ ] `uv lock --check` clean.
- [ ] `pytest tests/ -m "not live"` green.
- [ ] Dead-code tests cover the new deletes.
- [ ] Grep checks in Instructions are clean under `src/`.
- [ ] No new features.

---

## What this wave unblocks

Plan 21 is complete. Merge to `main`.
