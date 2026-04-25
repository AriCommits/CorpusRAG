# A4: Remove Dead Code

**Time:** 1 hr  
**Priority:** MEDIUM  
**Prerequisites:** A1, A2, A3 (ensure nothing depends on code being removed)

---

## Goal

Remove confirmed dead code: unused files, redundant CLI entry points, unused dependencies.

---

## Files to Delete

| File | Reason |
|------|--------|
| `src/utils/manage_keys.py` | Never imported, no CLI wiring |
| `src/utils/manage_secrets.py` | Never imported, no CLI wiring |
| `src/corpus_callosum/` | Ghost directory, only `__pycache__/` |

---

## Files to Modify

| File | Action |
|------|--------|
| `pyproject.toml` | Remove redundant entry points, unused deps |
| `src/config/schema.py` | Delete dead validators (~200 lines) |
| `src/cli.py` | Delete `bulk_export()` stub |

---

## Session 1: Delete Dead Files (15 min)

### Subtasks

- [ ] Delete `src/utils/manage_keys.py`
- [ ] Delete `src/utils/manage_secrets.py`
- [ ] Delete `src/corpus_callosum/` directory
- [ ] Verify no import errors

### Session Prompt

```
I'm implementing Plan 8, Task A4 from docs/plans/plan_8/A4-dead-code.md.

Goal: Delete confirmed dead files.

Please use Bash to:
1. Delete src/utils/manage_keys.py
2. Delete src/utils/manage_secrets.py
3. Delete the src/corpus_callosum/ directory (it only contains __pycache__)

Then verify nothing imports these:
- grep -r "from utils.manage_keys" src/
- grep -r "from utils.manage_secrets" src/
- grep -r "corpus_callosum" src/
```

### Verification

```bash
# Files gone
ls src/utils/manage_keys.py 2>&1 | grep -q "No such file" && echo "PASS" || echo "FAIL"
ls src/utils/manage_secrets.py 2>&1 | grep -q "No such file" && echo "PASS" || echo "FAIL"
ls src/corpus_callosum/ 2>&1 | grep -q "No such file" && echo "PASS" || echo "FAIL"

# No broken imports
python -c "import src" && echo "PASS: No import errors"
```

---

## Session 2: Clean pyproject.toml (20 min)

### Subtasks

- [ ] Remove 7 redundant CLI entry points
- [ ] Remove unused dependencies

### Session Prompt

```
I'm implementing Plan 8, Task A4 (Session 2) from docs/plans/plan_8/A4-dead-code.md.

Goal: Clean up pyproject.toml

Please:
1. Read pyproject.toml

2. In [project.scripts], KEEP only:
   - corpus = "cli:cli"
   - corpus-mcp-server = "mcp_server:main"
   
   REMOVE these redundant entry points:
   - corpus-rag
   - corpus-flashcards  
   - corpus-summaries
   - corpus-quizzes
   - corpus-video
   - corpus-orchestrate
   - corpus-db

3. In dependencies, REMOVE these (never imported):
   - pydantic
   - typer
   - rich
   - structlog
   - beautifulsoup4
   - markdownify
   - striprtf
   - python-docx

Show me the changes before applying.
```

### Verification

```bash
# Reinstall and verify
pip install -e .

# Verify corpus command works
corpus --help

# Verify removed deps not required
pip check
```

---

## Session 3: Delete Dead Validators (15 min)

### Subtasks

- [ ] Delete unused validator functions from schema.py
- [ ] Keep `_validate_config_keys()` (only one actually used)

### Session Prompt

```
I'm implementing Plan 8, Task A4 (Session 3) from docs/plans/plan_8/A4-dead-code.md.

Goal: Delete dead validator functions from src/config/schema.py

These functions are defined but NEVER called anywhere:
- validate_llm_config()
- validate_embedding_config()
- validate_database_config()
- validate_paths_config()
- validate_video_config()
- validate_config()

Please:
1. Read src/config/schema.py
2. Verify these are not called: grep -r "validate_llm_config\|validate_embedding_config\|validate_database_config\|validate_paths_config\|validate_video_config\|validate_config" src/
3. Delete all the unused validator functions
4. KEEP: _validate_config_keys() and ALLOWED_CONFIG_KEYS (these ARE used)

Show me what remains in the file after cleanup.
```

---

## Session 4: Delete bulk_export Stub (10 min)

### Subtasks

- [ ] Delete `bulk_export()` from cli.py (it's just placeholder comments)

### Session Prompt

```
I'm implementing Plan 8, Task A4 (Session 4) from docs/plans/plan_8/A4-dead-code.md.

Goal: Delete the bulk_export() stub from src/cli.py

This function (around lines 58-72) contains only placeholder comments like:
"# ... logic ..."

Please:
1. Read src/cli.py
2. Find the bulk_export command
3. Delete the entire function and its @cli.command() decorator

Show me the diff.
```

---

## Done When

- [ ] 3 files/directories deleted
- [ ] 7 CLI entry points removed from pyproject.toml
- [ ] 8 unused dependencies removed
- [ ] Dead validators deleted (~200 lines gone)
- [ ] bulk_export stub deleted
- [ ] `pip install -e .` succeeds
- [ ] `pytest tests/` passes
- [ ] Committed: `Plan 8 A4: Remove dead code and unused dependencies`
