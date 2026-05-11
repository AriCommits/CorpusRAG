# Sprint 6 — Documentation Scaffolding Pass

**Plan:** docs/plans/plan_18/OVERVIEW.md
**Wave:** 6 of 6
**Can run in parallel with:** none — depends on all prior sprints
**Must complete before:** (final)

---

## Agents in This Wave

### Agent A: D1 — Documentation Scaffolding Across All Touched Files

**Complexity:** S
**Estimated time:** 2 hours
**Files to modify:**
- `src/cli.py` — add/update module docstring
- `src/tools/__init__.py` — add module docstring
- `src/tools/cli.py` — add module docstring
- `src/tools/learning/__init__.py` — add module docstring
- `src/tools/learning/cli.py` — add module docstring
- `src/tools/flashcards/cli.py` — update module docstring
- `src/tools/quizzes/cli.py` — update module docstring
- `src/db/collections_cli.py` — update module docstring
- `src/db/management.py` — update module docstring
- `src/tools/rag/cli.py` — update module docstring
- `src/tools/rag/tui.py` — update module docstring
- `src/tools/rag/tui_collections.py` — update module docstring
- `src/tools/rag/doctor.py` — update module docstring
- `src/tools/rag/ingest.py` — update module docstring
- `src/CLI.md` — full rewrite to reflect new command hierarchy

**Depends on:** C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14
**Blocks:** none

**Instructions:**
For every file listed above, ensure it has a module-level docstring following this template:

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

For `src/CLI.md`, rewrite the document to reflect the new command hierarchy:
```
corpus
├── setup
├── doctor
├── benchmark
├── tools
│   ├── rag (ingest, sync, query, chat, ui)
│   ├── video (ingest, ingest-url, ...)
│   ├── handwriting (ingest, ...)
│   ├── summaries (generate, ...)
│   └── learning
│       ├── flashcards (generate, ...)
│       └── quizzes (generate, ...)
├── db (list, backup, export, restore, migrate)
├── collections (list, info, delete, manage, update-path)
└── dev (...)
```

Note that old top-level aliases (`corpus rag`, `corpus video`, etc.) have been removed entirely.

Add `# TODO(plan_18):` inline comments at any point where behavior changed significantly, so future developers can trace the change back to this plan.

**Definition of Done:**
- [ ] Every modified file has a module-level docstring
- [ ] `src/CLI.md` accurately reflects the new command tree
- [ ] `# TODO(plan_18):` comments mark behavioral changes
- [ ] No regressions in existing tests
