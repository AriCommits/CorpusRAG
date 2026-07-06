# Sprint 1 — Foundations (Config Core, Orchestrate Wiring, Config Docs, CI/Packaging)

**Plan:** docs/plans/plan_20/OVERVIEW.md
**Wave:** 1 of 3
**Can run in parallel with:** all agents in this wave (C1, O1, D2, P1 touch disjoint files)
**Must complete before:** Sprint 2 (C1 unblocks C2 & O2; O1 unblocks O2 & D1)

---

## Agents in This Wave

### Agent A: C1 — Config loader full-dict propagation

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/config/base.py` — add a `raw` field to `BaseConfig` and populate it in `from_dict`.
- `tests/test_config_raw_propagation.py` (NEW) — unit + property tests.

**Depends on:** none
**Blocks:** C2, O2

**Instructions:**
Add a non-comparable field to `BaseConfig`:
```python
raw: dict = field(default_factory=dict, compare=False, repr=False)
```
In `BaseConfig.from_dict(data)`, after constructing the typed sub-configs, set `inst.raw = data`
and return the instance. Do **not** change `to_dict()` — it must keep emitting only the four modeled
sections and masking `api_key` (display/logging and `merge_configs` rely on this).
Confirm subclasses (`FlashcardConfig`, `QuizConfig`, `SummaryConfig`, `VideoConfig`, `RAGConfig`)
still call `super().from_dict(data)` with the full dict — they now benefit automatically.

Write tests:
- Unit: `BaseConfig.from_dict(sample).raw == sample`; `to_dict()` output still contains only the four
  sections; equality/`repr` unaffected by `raw` (two configs with same modeled fields but different
  `raw` compare equal).
- Property (Hypothesis, ≥100 iterations), tagging comment
  `# Feature: project-hardening, Property 3: deep-merge override and retention semantics`:
  generate nested dicts (depth ≤ 5) `(base, override)` and assert `deep_merge` retains base-only keys,
  override wins on scalar/type conflict, and mapping+mapping merges recursively.

**Definition of Done:**
- [ ] `BaseConfig.raw` present, populated by `from_dict`, excluded from compare/repr.
- [ ] `to_dict()` behavior unchanged (four sections, masked secret).
- [ ] Deep-merge property test passes ≥100 iterations.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

### Agent B: O1 — Orchestrate CLI wiring + dead-code removal

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/cli.py` — register `orchestrate` in the root `lazy_subcommands`.
- `src/orchestrations/cli.py` — remove the `study_session` command; keep only `lecture_pipeline`;
  rebrand the group docstring to "CorpusRAG".
- `src/orchestrations/study_session.py` (DELETE)
- `src/orchestrations/knowledge_base.py` (DELETE)
- `src/orchestrations/__init__.py` — trim `__all__` and the lazy `__getattr__` map to
  `LecturePipelineOrchestrator` only.
- `tests/test_orchestrate_cli.py` (NEW)

**Depends on:** none
**Blocks:** O2 (shares `src/orchestrations/cli.py`), D1 (cli.txt reflects registration)

**Instructions:**
Add to the root group's `lazy_subcommands` in `src/cli.py`:
```python
"orchestrate": "orchestrations.cli:orchestrate",
```
In `src/orchestrations/cli.py`, delete the entire `study_session` command function and its options;
leave `lecture_pipeline` in place (O2 will modify its internals next wave). Delete the two dead
modules and update `__init__.py` so a full-text search for `KnowledgeBaseOrchestrator` /
`StudySessionOrchestrator` returns nothing outside a migration note. Grep the repo (including
`src/mcp_server/`) for any import of the removed classes and remove those references.

**IMPORTANT — do not touch `lecture_pipeline`'s body** beyond keeping it importable; O2 owns that file
next wave and will rewire its config. Keep your edits to `cli.py` limited to the one dict entry to
minimize the merge surface with O2.

Write tests: `CliRunner` runs `corpus orchestrate lecture-pipeline --help` (exit 0);
`orchestrate.list_commands(ctx) == ["lecture-pipeline"]`; `import
orchestrations.study_session` and `import orchestrations.knowledge_base` raise `ModuleNotFoundError`.

**Definition of Done:**
- [ ] `corpus orchestrate lecture-pipeline` resolves with no command-not-found/import error.
- [ ] `orchestrate` group exposes only `lecture-pipeline`.
- [ ] `StudySessionOrchestrator` and `KnowledgeBaseOrchestrator` deleted; no lingering imports.
- [ ] `LecturePipelineOrchestrator` still imports.
- [ ] Tests written and passing; no regressions.

---

### Agent C: D2 — Configuration docs rewrite + env cleanup

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `docs/configuration.md` — align to the real schema and entry points.
- `configs/.env.example` — rebrand header.

**Depends on:** none
**Blocks:** none (V1 will validate)

**Instructions:**
Rewrite `docs/configuration.md` so it matches the code:
- Field names: use `child_chunk_size`/`child_chunk_overlap` (not `chunking.size`), `summary_length`
  (not `default_length`), `whisper_model` (not `transcription.model`), and the actual
  flashcards/quizzes field names. Cross-check every documented key against
  `configs/base.example.yaml` and the tool config dataclasses.
- Remove all references to non-existent commands: `corpus-config`, `corpus-config
  show/validate/sources`, `corpus-secrets`. Only `corpus` and `corpus-mcp-server` exist.
- Remove the `corpus_callosum.config.base` import example (module does not exist).
- Document the env override prefix as `CC_`.
- Backend values: `ollama` | `openai_compatible` | `anthropic_compatible` only.
- Rebrand every "CorpusCallosum"/"Corpus Callosum" → "CorpusRAG".
Rebrand the `configs/.env.example` header comment to CorpusRAG.

Do **not** edit `configs/base.example.yaml` (owned by C2) or `README.md`/`src/CLI.md` (owned by D1).

**Definition of Done:**
- [ ] Zero occurrences of `corpus-config`, `corpus-secrets`, `corpus_callosum.config.base`.
- [ ] Zero occurrences of "CorpusCallosum"/"Corpus Callosum" in the two files.
- [ ] Documented config keys match current schema field names.
- [ ] `CC_` prefix documented; only valid backend values shown.
- [ ] No regressions (docs-only change).

---

### Agent D: P1 — CI reliability + dependency/packaging cleanup

**Complexity:** L
**Estimated time:** 3 hours
**Files to modify:**
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `uv.lock` (regenerate)

**Depends on:** none
**Blocks:** none (V1 validates final green CI)

**Instructions:**
In `pyproject.toml`:
- Remove `ruff` from the core `dependencies` list (keep the single pin in the `dev` extra).
- Add a CPU index and make torch sources conditional:
  ```toml
  [[tool.uv.index]]
  name = "pytorch-cpu"
  url = "https://download.pytorch.org/whl/cpu"
  explicit = true
  # keep the existing pytorch-cu128 index

  [tool.uv.sources]
  torch = [
    { index = "pytorch-cpu",   marker = "sys_platform == 'linux'" },
    { index = "pytorch-cu128", marker = "sys_platform == 'win32'" },
  ]
  # mirror the two-marker mapping for torchvision and torchaudio
  ```
- Remove `[tool.mypy]` and its `[[tool.mypy.overrides]]` blocks entirely (D4).
- Correct the `server` optional-dependency group comment: it is **not** torch-free; state the real
  footprint includes `torch`, `faster-whisper`, and `transformers` (sentence-transformers requires
  torch).

In `.github/workflows/ci.yml`:
- Delete the `CORPUSRAG_CONFIG: configs/base.yaml` env block from the test job (nothing reads it).
- Add a `deptry` step to the lint job (e.g., `uv run deptry src`), after `ruff` checks. Ensure
  `deptry` is available (it is configured in `pyproject.toml`; add it to the `dev` extra if missing).

Regenerate the lock: run `uv lock` locally and confirm `uv lock --check` exits 0.

**Definition of Done:**
- [ ] Exactly one `ruff` pin (dev extra only); no package duplicated across core + dev.
- [ ] Linux resolves CPU torch wheels; Windows still CUDA; `uv lock --check` passes.
- [ ] `[tool.mypy]` removed; `deptry` runs in the lint job and is green.
- [ ] Dead `CORPUSRAG_CONFIG` env removed from CI.
- [ ] `server` group documentation states its real torch footprint.
- [ ] No regressions.
