# T3: Create Learn Tools — `mcp_server/tools/learn.py`

**Sprint:** 1 (Parallel)
**Time:** 1.5 hrs
**Prerequisites:** None
**Parallel-safe with:** T1, T2 (all create NEW files, zero overlap)

---

## Goal

Extract flashcard, summary, quiz, and video tool functions from the monolithic `server.py` into standalone, transport-agnostic functions in `mcp_server/tools/learn.py`.

---

## Files to Create

| File | Action |
|------|--------|
| `src/mcp_server/tools/learn.py` | NEW — learning tool functions |
| `tests/unit/test_mcp_learn_tools.py` | NEW — unit tests |

---

## Design

### Public API

```python
def generate_flashcards(collection: str, count: int, difficulty: str, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Generate flashcards from a collection."""

def generate_summary(collection: str, topic: str | None, length: str, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Generate a summary from a collection."""

def generate_quiz(collection: str, count: int, question_types: list[str] | None, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Generate a quiz from a collection."""

def transcribe_video(video_path: str, collection: str, model: str, config: BaseConfig, db: DatabaseBackend) -> dict:
    """Transcribe a video file using Whisper."""

def clean_transcript(transcript_text: str, model: str | None, config: BaseConfig) -> dict:
    """Clean and format a transcript using LLM."""
```

### Key Constraints

- **No FastAPI imports** — pure functions
- **No auth** — auth is handled by middleware/profiles layer
- **Explicit deps** — every function receives `config` and `db` as args
- **Return dicts** — `{"status": "success", ...}` or `{"status": "error", "error": "..."}`
- **Handle missing extras gracefully** — flashcards/summaries/quizzes require `generators` extra; return clear error dict if not installed

---

## Implementation Details

### Handling Optional Dependencies

The generators require `tiktoken` (the `generators` extra). The current `tools/flashcards/__init__.py` already has `GENERATORS_AVAILABLE` flag. Use the same pattern:

```python
def generate_flashcards(collection, count, difficulty, config, db):
    try:
        from tools.flashcards import FlashcardConfig, FlashcardGenerator, GENERATORS_AVAILABLE
    except ImportError:
        return {"status": "error", "error": "Flashcard generation requires 'generators' extra. Install: pip install corpusrag[generators]"}

    if not GENERATORS_AVAILABLE:
        return {"status": "error", "error": "Flashcard generation requires 'generators' extra. Install: pip install corpusrag[generators]"}

    # ... proceed with generation
```

### Extraction Pattern

For each function, extract from `server.py`:
1. Remove `auth_context` parameter and `Depends()` reference
2. Remove `auth_context["key_info"]["name"]` from return values
3. Add input validation using `utils.validation.get_validator()` directly
4. Wrap validation errors as `{"status": "error", "error": "..."}` dicts
5. Keep the tool config creation pattern (e.g., `FlashcardConfig.from_dict(config.to_dict())`)

### Reference: Current server.py Functions (lines to extract from)

- `generate_flashcards` (~lines 200-240): Creates FlashcardConfig, FlashcardGenerator, calls generate()
- `generate_summary` (~lines 242-290): Creates SummaryConfig, SummaryGenerator, calls generate()
- `generate_quiz` (~lines 292-335): Creates QuizConfig, QuizGenerator, calls generate()
- `transcribe_video` (~lines 337-365): Creates VideoConfig, VideoTranscriber, calls transcribe_file()
- `clean_transcript` (~lines 367-390): Creates VideoConfig, TranscriptCleaner, calls clean()

---

## Tests

### `tests/unit/test_mcp_learn_tools.py`

```python
"""Tests for mcp_server.tools.learn — learning MCP tools."""

import pytest
import yaml


@pytest.fixture()
def learn_config(tmp_path):
    """Create config for learn tool tests."""
    cfg_data = {
        "llm": {"model": "test-model"},
        "database": {
            "mode": "persistent",
            "persist_directory": str(tmp_path / "chroma"),
        },
    }
    cfg_path = tmp_path / "base.yaml"
    cfg_path.write_text(yaml.dump(cfg_data))
    return str(cfg_path)


class TestGenerateFlashcards:
    def test_missing_generators_returns_error(self, learn_config):
        """If generators extra not installed, should return error dict."""
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.tools.learn import generate_flashcards

        config = load_config(learn_config)
        db = ChromaDBBackend(config.database)
        result = generate_flashcards("notes", 10, "medium", config, db)
        # Either succeeds or returns clear error about missing extra
        assert result["status"] in ("success", "error")
        if result["status"] == "error":
            assert "generators" in result["error"].lower() or "collection" in result["error"].lower()

    def test_returns_dict_structure(self, learn_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.tools.learn import generate_flashcards

        config = load_config(learn_config)
        db = ChromaDBBackend(config.database)
        result = generate_flashcards("nonexistent", 5, "easy", config, db)
        assert isinstance(result, dict)
        assert "status" in result


class TestGenerateSummary:
    def test_returns_dict_structure(self, learn_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.tools.learn import generate_summary

        config = load_config(learn_config)
        db = ChromaDBBackend(config.database)
        result = generate_summary("nonexistent", None, "medium", config, db)
        assert isinstance(result, dict)
        assert "status" in result


class TestGenerateQuiz:
    def test_returns_dict_structure(self, learn_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.tools.learn import generate_quiz

        config = load_config(learn_config)
        db = ChromaDBBackend(config.database)
        result = generate_quiz("nonexistent", 5, None, config, db)
        assert isinstance(result, dict)
        assert "status" in result


class TestCleanTranscript:
    def test_returns_dict_structure(self, learn_config):
        from config import load_config
        from mcp_server.tools.learn import clean_transcript

        config = load_config(learn_config)
        result = clean_transcript("raw transcript text", None, config)
        assert isinstance(result, dict)
        assert "status" in result


class TestNoFastapiImports:
    def test_no_fastapi_in_module(self):
        """Verify learn.py has no FastAPI imports."""
        import ast
        from pathlib import Path

        source = Path("src/mcp_server/tools/learn.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "fastapi" not in node.module.lower()
```

---

## Session Prompt

```
I'm implementing Plan 9, Task T3 from docs/plans/plan_9/S1-T3-learn-tools.md.

Goal: Create mcp_server/tools/learn.py with learning-focused MCP tool functions.

Please:
1. Read docs/plans/plan_9/S1-T3-learn-tools.md completely
2. Read src/mcp_server/server.py — specifically the generate_flashcards, generate_summary,
   generate_quiz, transcribe_video, and clean_transcript functions
3. Read src/tools/flashcards/__init__.py to see the GENERATORS_AVAILABLE pattern
4. Create src/mcp_server/tools/learn.py extracting those 5 functions with:
   - No auth_context parameter
   - No Depends() references
   - Explicit config + db args
   - Graceful handling of missing generators extra
   - All return {"status": "success"|"error", ...} dicts
5. Create tests/unit/test_mcp_learn_tools.py
6. Run tests and fix issues

Key constraint: NO FastAPI imports. Handle missing optional extras gracefully.
```

---

## Verification

```bash
pytest tests/unit/test_mcp_learn_tools.py -v
grep -r "fastapi" src/mcp_server/tools/learn.py && echo "FAIL" || echo "PASS"
```

---

## Done When

- [ ] `src/mcp_server/tools/learn.py` has all 5 functions
- [ ] Missing `generators` extra returns clear error dict (not ImportError)
- [ ] No FastAPI imports
- [ ] `tests/unit/test_mcp_learn_tools.py` passes
- [ ] Existing tests still pass
