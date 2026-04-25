# P4: Enhanced Token Counting from LLM Responses

**Time:** 1 hr  
**Priority:** LOW  
**Prerequisites:** P1, P2

---

## Goal

Extract actual token counts from LLM API responses (Ollama, OpenAI, Anthropic) instead of estimating.

---

## Files to Modify

| File | Action |
|------|--------|
| `src/llm/backend.py` | Extract token counts from API responses |
| `src/tools/rag/agent.py` | Propagate counts to MessageMetadata |

---

## Session 1: Extract Tokens from Ollama (30 min)

### Session Prompt

```
I'm implementing Plan 8, Task P4 from docs/plans/plan_8/P4-token-counting.md.

Goal: Extract token counts from Ollama API responses.

Please update src/llm/backend.py OllamaBackend:

1. Add instance variables:
   self._last_prompt_tokens = 0
   self._last_completion_tokens = 0

2. In _stream_request(), when data.get("done") is True:
   - Extract: self._last_prompt_tokens = data.get("prompt_eval_count", 0)
   - Extract: self._last_completion_tokens = data.get("eval_count", 0)

3. Update complete() to return LLMResponse with:
   prompt_tokens=self._last_prompt_tokens,
   completion_tokens=self._last_completion_tokens

Apply similar pattern to OpenAICompatibleBackend and AnthropicCompatibleBackend.
```

---

## Session 2: Propagate to Metadata (20 min)

### Session Prompt

```
I'm implementing Plan 8, Task P4 (Session 2).

Update src/tools/rag/agent.py chat_with_metadata():

After getting LLM response, extract token counts:
- prompt_tokens = getattr(response, 'prompt_tokens', 0) or estimate_tokens(prompt)
- completion_tokens = getattr(response, 'completion_tokens', 0) or estimate_tokens(response_text)

Add to metadata dict returned.
```

---

## Done When

- [ ] Ollama returns actual token counts
- [ ] OpenAI-compatible returns actual token counts
- [ ] Falls back to estimation if not available
- [ ] Token counts shown in context sidebar
- [ ] Committed: `Plan 8 P4: Extract token counts from LLM responses`
