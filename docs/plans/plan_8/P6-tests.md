# P6: Tests & Final Verification

**Time:** 1-2 hrs  
**Priority:** HIGH  
**Prerequisites:** All other phases complete

---

## Goal

Comprehensive tests for all Plan 8 features.

---

## Files to Create

| File | Tests |
|------|-------|
| `tests/unit/test_tokens.py` | Token estimation accuracy |
| `tests/unit/test_tui_context.py` | Context block calculations |
| `tests/unit/test_message_metadata.py` | Metadata dataclass |

---

## Session 1: Token Estimation Tests (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P6 from docs/plans/plan_8/P6-tests.md.

Goal: Test token estimation utilities.

Create tests/unit/test_tokens.py:

import pytest
from utils.tokens import estimate_tokens, format_tokens

def test_estimate_tokens_nonempty():
    assert estimate_tokens("Hello world") > 0

def test_estimate_tokens_empty():
    assert estimate_tokens("") >= 0

def test_estimate_tokens_long_text():
    text = "word " * 1000
    tokens = estimate_tokens(text)
    # Should be roughly 1000-1500 tokens
    assert 500 < tokens < 2000

def test_format_tokens_small():
    assert format_tokens(500) == "500"

def test_format_tokens_thousands():
    assert format_tokens(1500) == "1.5k"
    assert format_tokens(10000) == "10.0k"
```

---

## Session 2: Context Sidebar Tests (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P6 (Session 2).

Create tests/unit/test_tui_context.py:

Test ContextBlock and ContextSidebar:
- test_context_block_percentage: verify percentage calculation
- test_context_sidebar_total_tokens: verify sum is correct
- test_empty_messages_handled: no crash on empty list
```

---

## Session 3: Integration Verification (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P6 (Session 3).

Run full verification:
1. ruff check src/ tests/
2. ruff format --check src/ tests/
3. pytest tests/ -v --ignore=tests/test_smoke.py
4. Manual TUI test checklist
```

---

## Manual Test Checklist

- [ ] Start TUI: `corpus rag chat --collection test`
- [ ] Send message, verify timer counts up
- [ ] Verify tags appear on response
- [ ] Press F3, verify context sidebar appears
- [ ] Verify token counts shown for each message
- [ ] Toggle message exclusion, verify visual change
- [ ] Send another message, verify excluded ones not in context
- [ ] Run `/context` command
- [ ] Run `/strategy` command

---

## Done When

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Ruff checks pass
- [ ] Manual testing complete
- [ ] Committed: `Plan 8 P6: Add tests for TUI enhancements`
