# A1: Fix Broken Generators

**Time:** 2-3 hrs (split into 3-4 sessions)  
**Priority:** CRITICAL  
**Prerequisites:** None (but do A3 first for quick win)

---

## Goal

Make flashcard, summary, and quiz generators work with real document data. Currently they silently fall back to placeholder/fake content.

---

## Root Cause

All three generators do this:

```python
if not sample_docs or not sample_docs.get("documents"):
    return self._generate_placeholder_flashcards(...)  # SILENT FAILURE
```

Users get fake content with no indication anything is wrong.

---

## Fix Strategy

1. Remove placeholder fallback methods entirely
2. Add proper validation of ChromaDB response structure
3. Raise clear `ValueError` with actionable message
4. Let LLM errors propagate (don't swallow with try/except)

---

## Files to Modify

| File | Action |
|------|--------|
| `src/tools/flashcards/generator.py` | Fix `generate()`, delete `_generate_placeholder_flashcards()` |
| `src/tools/summaries/generator.py` | Fix `generate()`, delete `_generate_placeholder_summary()` |
| `src/tools/quizzes/generator.py` | Fix `generate()`, delete `_generate_placeholder_questions()` |
| `tests/integration/test_generators.py` | NEW — Integration tests |

---

## Session 1: Fix FlashcardGenerator (45 min)

### Subtasks

- [ ] Update `generate()` to validate ChromaDB response
- [ ] Remove try/except that swallows errors (lines 93-96)
- [ ] Delete `_generate_placeholder_flashcards()` method (lines 197-220)
- [ ] Test manually

### Session Prompt

```
I'm implementing Plan 8, Task A1 from docs/plans/plan_8/A1-fix-generators.md.

Goal: Fix FlashcardGenerator to fail loudly instead of returning fake data.

Please:
1. Read src/tools/flashcards/generator.py completely
2. Modify the generate() method:
   - After self.db.query(), validate that sample_docs has actual documents
   - If no documents: raise ValueError with message like:
     "No documents found in '{collection}'. Run: corpus rag ingest --collection {name}"
   - Remove the try/except block (lines ~93-96) that catches all errors and returns placeholders
3. Delete the _generate_placeholder_flashcards() method entirely (lines ~197-220)
4. Keep _generate_with_llm() and _parse_flashcard_response() unchanged

Show me the diff before applying.
```

### Verification

```bash
# Should raise ValueError (no collection exists)
python -c "
from tools.flashcards import FlashcardConfig, FlashcardGenerator
from db import get_database
cfg = FlashcardConfig.from_dict({})
db = get_database(cfg.database)
gen = FlashcardGenerator(cfg, db)
gen.generate('nonexistent')
" 2>&1 | grep -q "ValueError" && echo "PASS: Raises error" || echo "FAIL"

# Should NOT contain "Placeholder"
python -c "
from tools.flashcards.generator import FlashcardGenerator
import inspect
print('Placeholder' not in inspect.getsource(FlashcardGenerator))
" | grep -q "True" && echo "PASS: No placeholder method" || echo "FAIL"
```

---

## Session 2: Fix SummaryGenerator (30 min)

### Subtasks

- [ ] Apply same pattern as FlashcardGenerator
- [ ] Delete `_generate_placeholder_summary()` method
- [ ] Test manually

### Session Prompt

```
I'm implementing Plan 8, Task A1 (Session 2) from docs/plans/plan_8/A1-fix-generators.md.

Goal: Fix SummaryGenerator using the same pattern as FlashcardGenerator.

The FlashcardGenerator was already fixed to:
- Validate ChromaDB response structure
- Raise ValueError if no documents found
- Remove placeholder fallback

Please:
1. Read src/tools/summaries/generator.py
2. Apply the same fix pattern to generate():
   - Validate documents exist after db.query()
   - Raise clear ValueError if empty
   - Remove any try/except that swallows errors
3. Delete any _generate_placeholder_* method
4. Match the error message style from flashcards

Show me the diff before applying.
```

### Verification

```bash
python -c "
from tools.summaries import SummaryConfig, SummaryGenerator
from db import get_database
cfg = SummaryConfig.from_dict({})
db = get_database(cfg.database)
gen = SummaryGenerator(cfg, db)
gen.generate('nonexistent')
" 2>&1 | grep -q "ValueError" && echo "PASS" || echo "FAIL"
```

---

## Session 3: Fix QuizGenerator (30 min)

### Subtasks

- [ ] Apply same pattern as FlashcardGenerator
- [ ] Delete `_generate_placeholder_questions()` method
- [ ] Test manually

### Session Prompt

```
I'm implementing Plan 8, Task A1 (Session 3) from docs/plans/plan_8/A1-fix-generators.md.

Goal: Fix QuizGenerator using the same pattern as FlashcardGenerator.

Please:
1. Read src/tools/quizzes/generator.py
2. Apply the same fix pattern to generate():
   - Validate documents exist after db.query()
   - Raise clear ValueError if empty
   - Remove any try/except that swallows errors
3. Delete any _generate_placeholder_* method

Show me the diff before applying.
```

---

## Session 4: Add Integration Tests (45 min)

### Subtasks

- [ ] Create `tests/integration/test_generators.py`
- [ ] Test generators with real ingested documents
- [ ] Test error cases (empty collection, nonexistent collection)

### Session Prompt

```
I'm implementing Plan 8, Task A1 (Session 4) from docs/plans/plan_8/A1-fix-generators.md.

Goal: Write integration tests for the fixed generators.

Please create tests/integration/test_generators.py with:

1. A pytest fixture that:
   - Creates a temporary ChromaDB collection
   - Ingests 2-3 sample markdown documents with real content
   - Yields the collection name
   - Cleans up after

2. Tests for FlashcardGenerator:
   - test_generate_from_real_documents: generates cards, verifies no "Placeholder" in output
   - test_empty_collection_raises_valueerror
   - test_nonexistent_collection_raises_valueerror

3. Similar tests for SummaryGenerator and QuizGenerator

Use the existing test patterns from tests/integration/test_rag_integration.py as reference.
```

### Verification

```bash
pytest tests/integration/test_generators.py -v
```

---

## Done When

- [ ] All 3 generators raise clear errors when no documents
- [ ] No `_generate_placeholder_*` methods exist
- [ ] Integration tests pass
- [ ] Manual test with real collection works
- [ ] Committed: `Plan 8 A1: Fix generators to use real documents`
