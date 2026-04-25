# P5: Security & UX Hardening

**Time:** 1-2 hrs  
**Priority:** MEDIUM  
**Prerequisites:** P1-P3

---

## Goal

Security review of new features, plus UX polish.

---

## Subtasks

### Security
- [ ] Validate message IDs (UUID format only)
- [ ] Add session file checksum for integrity
- [ ] Rate limit context toggle sync (prevent UI lag)

### UX
- [ ] Show retrieval strategy in footer
- [ ] Flash context bar yellow at 80% usage
- [ ] Add undo toast after excluding messages

---

## Session 1: Input Validation (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P5 from docs/plans/plan_8/P5-security-ux.md.

Goal: Add security validations.

1. In src/tools/rag/tui.py, add:
   import re
   def _validate_message_id(message_id: str) -> bool:
       return bool(re.match(r"^[a-f0-9\-]{36}$", message_id))

2. In src/tools/rag/session.py, add checksum validation:
   - On save: compute SHA256 of JSON, store first 16 chars
   - On load: verify checksum, return empty if mismatch

3. Add rate limiting decorator for _sync_context_sidebar()
```

---

## Session 2: UX Improvements (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P5 (Session 2).

Goal: Add UX improvements.

1. Show current strategy in Footer:
   - Update Footer to show: "Strategy: hybrid | Collection: xyz"

2. Context warning at 80%:
   - In ContextSidebar, if usage > 80%, add "warning" class to progress bar
   - CSS: ProgressBar.warning { background: $warning; }

3. Strategy in sidebar:
   - Add label showing current RAG strategy below context header
```

---

## Done When

- [ ] Invalid message IDs rejected
- [ ] Corrupted sessions detected
- [ ] No UI lag from rapid toggles
- [ ] Strategy visible in UI
- [ ] 80% warning visible
- [ ] Committed: `Plan 8 P5: Security hardening and UX improvements`
