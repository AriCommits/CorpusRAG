# A3: Fix MCP Server & Orchestrator Attribute Errors

**Time:** 30 min  
**Priority:** HIGH (blocks other work)  
**Prerequisites:** None

---

## Goal

Fix 4 wrong attribute references that cause `AttributeError` at runtime.

---

## Files to Modify

| File | Line(s) | Issue |
|------|---------|-------|
| `src/mcp_server/server.py` | ~155 | `rag_config.retrieval.top_k` → `top_k_final` |
| `src/mcp_server/server.py` | ~386 | `video_config.whisper.model` → `whisper_model` |
| `src/mcp_server/server.py` | ~418 | `video_config.ollama_cleaning.model` → `clean_model` |
| `src/orchestrations/knowledge_base.py` | ~50 | `result.documents_processed` → `files_indexed` |

---

## Subtasks

- [ ] Fix `rag_config.retrieval.top_k` → `rag_config.retrieval.top_k_final`
- [ ] Fix `video_config.whisper.model` → `video_config.whisper_model`
- [ ] Fix `video_config.ollama_cleaning.model` → `video_config.clean_model`
- [ ] Fix `result.documents_processed` → `result.files_indexed`

---

## Session Prompt

```
I'm implementing Plan 8, Task A3 from docs/plans/plan_8/A3-mcp-fixes.md.

Goal: Fix 4 attribute reference errors that cause runtime crashes.

Please:
1. Read src/mcp_server/server.py
2. Find and fix these wrong references:
   - rag_config.retrieval.top_k → rag_config.retrieval.top_k_final
   - video_config.whisper.model → video_config.whisper_model
   - video_config.ollama_cleaning.model → video_config.clean_model
3. Read src/orchestrations/knowledge_base.py
4. Fix: result.documents_processed → result.files_indexed

Only fix these 4 specific issues. Do not refactor anything else.
```

---

## Verification

```bash
# 1. Import test (no AttributeError)
python -c "from mcp_server.server import mcp; print('MCP imports OK')"

# 2. Import orchestrator
python -c "from orchestrations.knowledge_base import KnowledgeBaseOrchestrator; print('Orchestrator imports OK')"

# 3. Run related tests
pytest tests/test_mcp_tools.py -v
```

---

## Done When

- [ ] All 4 imports succeed without error
- [ ] Tests pass
- [ ] Committed with message: `Plan 8 A3: Fix MCP and orchestrator attribute references`
