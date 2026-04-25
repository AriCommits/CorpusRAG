# P3: Selective Message Inclusion/Exclusion

**Time:** 2 hrs  
**Priority:** MEDIUM  
**Prerequisites:** P2 (needs context sidebar)

---

## Goal

Allow users to include/exclude message pairs from active context via toggles in chat and sidebar.

---

## Files to Modify

| File | Action |
|------|--------|
| `src/tools/rag/session.py` | Add `included` field to session schema |
| `src/tools/rag/tui.py` | Add toggle to ChatMessage, handle events |
| `src/tools/rag/tui_context.py` | Add toggle to ContextBlock |
| `src/tools/rag/agent.py` | Filter excluded messages from LLM prompt |
| `src/tools/rag/slash_commands.py` | Add `/context` command |

---

## Session 1: Extend Session Schema (20 min)

### Session Prompt

```
I'm implementing Plan 8, Task P3 from docs/plans/plan_8/P3-selective-context.md.

Goal: Add 'included' field to session message schema.

Please update src/tools/rag/session.py:

1. Update save_session() to handle messages with 'included' field
2. Update load_session() to default 'included' to True for backward compat
3. The session JSON should support:
   {"role": "user", "content": "...", "included": true}
```

---

## Session 2: Add Toggle to ChatMessage (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P3 (Session 2).

Goal: Add inclusion toggle to ChatMessage widget.

Please update src/tools/rag/tui.py:

1. Import Switch from textual.widgets
2. Add to ChatMessage:
   - included_in_context = reactive(True)
   - Add Switch widget in compose()
3. Handle Switch.Changed to update included_in_context
4. Add CSS for excluded messages (opacity: 0.5, left border)
5. Post custom message when toggle changes for parent to handle
```

---

## Session 3: Add Context Filtering to Agent (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P3 (Session 3).

Goal: Filter excluded messages from LLM prompt.

Please update src/tools/rag/agent.py:

1. Add _filter_context() method:
   def _filter_context(self, history: list[dict]) -> list[dict]:
       return [msg for msg in history if msg.get("included", True)]

2. In query(), filter conversation_history before building prompt
```

---

## Session 4: Add /context Slash Command (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P3 (Session 4).

Goal: Add /context slash command.

Please update src/tools/rag/slash_commands.py:

Add command with subcommands:
- /context - Show usage stats
- /context show - Toggle sidebar
- /context clear - Exclude all except last exchange  
- /context include all - Include all messages
```

---

## Done When

- [ ] Toggle switches appear on messages
- [ ] Excluded messages visually distinct (dimmed)
- [ ] Toggling user message toggles paired assistant message
- [ ] Excluded messages not sent to LLM
- [ ] `/context` command works
- [ ] Session persistence includes `included` state
- [ ] Committed: `Plan 8 P3: Add selective context inclusion/exclusion`
