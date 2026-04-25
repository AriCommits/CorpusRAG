# A5: Optional Extras for Public/Personal Builds

**Time:** 1-2 hrs  
**Priority:** LOW (do last)  
**Prerequisites:** A4 (needs clean dependency list)

---

## Goal

Allow separation of full personal build from minimal public release using pip extras.

```bash
pip install corpus-rag          # Public: RAG + TUI + MCP
pip install corpus-rag[full]    # Personal: Everything
```

---

## Files to Modify

| File | Action |
|------|--------|
| `pyproject.toml` | Add optional-dependencies sections |
| `src/tools/flashcards/__init__.py` | Add feature availability check |
| `src/tools/summaries/__init__.py` | Add feature availability check |
| `src/tools/quizzes/__init__.py` | Add feature availability check |
| `src/cli.py` | Add graceful fallbacks for missing features |

---

## Session 1: Define Extras in pyproject.toml (20 min)

### Subtasks

- [ ] Add `[project.optional-dependencies]` section
- [ ] Define `generators`, `video`, `full` extras

### Session Prompt

```
I'm implementing Plan 8, Task A5 from docs/plans/plan_8/A5-optional-extras.md.

Goal: Add optional dependency groups to pyproject.toml

Please:
1. Read pyproject.toml
2. Add a [project.optional-dependencies] section with:

   generators = [
       "tiktoken>=0.5",
   ]
   
   video = [
       "faster-whisper>=0.9",
   ]
   
   full = [
       "corpus-rag[generators]",
       "corpus-rag[video]",
   ]
   
   dev = [
       "pytest>=7.0",
       "pytest-asyncio>=0.21",
       "ruff>=0.1",
   ]

Move any dev-only dependencies from main dependencies to the dev extra.
```

### Verification

```bash
# Verify extras parse correctly
pip install -e ".[full]"
pip install -e ".[generators]"
```

---

## Session 2: Add Feature Checks to Generator Modules (30 min)

### Subtasks

- [ ] Add availability check to flashcards `__init__.py`
- [ ] Add availability check to summaries `__init__.py`
- [ ] Add availability check to quizzes `__init__.py`

### Session Prompt

```
I'm implementing Plan 8, Task A5 (Session 2) from docs/plans/plan_8/A5-optional-extras.md.

Goal: Add feature availability checks to generator modules.

Please update src/tools/flashcards/__init__.py:

1. Add a check function at the top:
   def _check_available():
       try:
           import tiktoken
           return True
       except ImportError:
           return False
   
   GENERATORS_AVAILABLE = _check_available()

2. Wrap the imports conditionally:
   if GENERATORS_AVAILABLE:
       from .config import FlashcardConfig
       from .generator import FlashcardGenerator
       __all__ = ["FlashcardConfig", "FlashcardGenerator"]
   else:
       __all__ = []

3. Add stub classes that raise helpful ImportError when generators extra not installed

Apply the same pattern to:
- src/tools/summaries/__init__.py
- src/tools/quizzes/__init__.py
```

---

## Session 3: Add CLI Fallbacks (30 min)

### Subtasks

- [ ] Make flashcards CLI show helpful message if not installed
- [ ] Same for summaries and quizzes CLIs

### Session Prompt

```
I'm implementing Plan 8, Task A5 (Session 3) from docs/plans/plan_8/A5-optional-extras.md.

Goal: Make CLI commands show helpful messages when extras not installed.

Please update src/cli.py:

For the flashcards, summaries, and quizzes command groups, wrap the import in try/except:

try:
    from tools.flashcards.cli import flashcards
    cli.add_command(flashcards)
except ImportError:
    @cli.group()
    def flashcards():
        """Flashcard generation (requires 'generators' extra)."""
        pass
    
    @flashcards.command()
    def generate():
        """Generate flashcards."""
        click.echo("Flashcard generation requires the 'generators' extra.")
        click.echo("Install with: pip install corpus-rag[generators]")
        raise SystemExit(1)

Apply same pattern for summaries and quizzes.
```

---

## Done When

- [ ] `pip install corpus-rag` works (minimal)
- [ ] `pip install corpus-rag[full]` works (everything)
- [ ] `corpus flashcards generate` shows helpful message when extra not installed
- [ ] All generators work when `[full]` installed
- [ ] Committed: `Plan 8 A5: Add optional extras for public/personal builds`
