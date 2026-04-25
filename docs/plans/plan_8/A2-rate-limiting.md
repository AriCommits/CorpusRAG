# A2: Wire Up Rate Limiting

**Time:** 1-2 hrs  
**Priority:** HIGH  
**Prerequisites:** None

---

## Goal

Connect the existing `src/utils/rate_limiting.py` module to LLM backends for cloud API protection (OpenAI, Anthropic, etc.).

---

## Current State

`rate_limiting.py` exists with a complete `OperationRateLimiter` class but is never used anywhere except tests.

---

## Files to Modify

| File | Action |
|------|--------|
| `src/config/base.py` | Add `rate_limit_rpm`, `rate_limit_concurrent` to LLMConfig |
| `configs/base.yaml` | Add rate limit config with examples |
| `src/llm/backend.py` | Integrate rate limiter into base class |

---

## Session 1: Add Config Fields (20 min)

### Subtasks

- [ ] Add `rate_limit_rpm: int | None` to LLMConfig
- [ ] Add `rate_limit_concurrent: int | None` to LLMConfig
- [ ] Add to YAML with documentation

### Session Prompt

```
I'm implementing Plan 8, Task A2 from docs/plans/plan_8/A2-rate-limiting.md.

Goal: Add rate limiting config fields to LLMConfig.

Please:
1. Read src/config/base.py, find the LLMConfig dataclass
2. Add two new optional fields:
   - rate_limit_rpm: int | None = None  # Requests per minute
   - rate_limit_concurrent: int | None = None  # Max concurrent requests
3. Read configs/base.yaml
4. Add these fields under the llm: section with comments explaining:
   - null = unlimited (default, for local Ollama)
   - 60 = typical OpenAI tier 1 limit
   - Include example for cloud vs local

Only modify these two files. Do not touch backend.py yet.
```

### Verification

```bash
python -c "
from config.base import LLMConfig
c = LLMConfig(rate_limit_rpm=60, rate_limit_concurrent=5)
print(f'RPM: {c.rate_limit_rpm}, Concurrent: {c.rate_limit_concurrent}')
"
```

---

## Session 2: Integrate into LLM Backend (45 min)

### Subtasks

- [ ] Import rate limiter in backend.py
- [ ] Initialize in `LLMBackend.__init__()` if limits configured
- [ ] Add `_check_rate_limit()` method with blocking/wait
- [ ] Add `_start_request()` / `_end_request()` for concurrent tracking
- [ ] Call from `complete()` and `chat()`

### Session Prompt

```
I'm implementing Plan 8, Task A2 (Session 2) from docs/plans/plan_8/A2-rate-limiting.md.

Goal: Wire rate limiter into LLMBackend.

Please:
1. Read src/utils/rate_limiting.py to understand the OperationRateLimiter API
2. Read src/llm/backend.py
3. Modify LLMBackend base class:
   
   In __init__():
   - Import and instantiate OperationRateLimiter if config has rate_limit_rpm or rate_limit_concurrent
   - Store as self._rate_limiter (None if no limits)
   
   Add helper methods:
   - _check_rate_limit(): Check RPM limit, wait if exceeded (log "Rate limited, waiting Xs...")
   - _start_request(): Call rate_limiter.start_operation() for concurrent tracking
   - _end_request(): Call rate_limiter.end_operation()
   
   Modify complete() method:
   - Call _check_rate_limit() before request
   - Wrap in try/finally with _start_request()/_end_request()
   
   Modify chat() method:
   - Same pattern

4. Use user_id="default" and operation_type="llm" for rate limiter calls

Keep changes minimal. Don't refactor unrelated code.
```

### Verification

```bash
# Unit test
python -c "
from llm.backend import OllamaBackend
from llm.config import LLMConfig

# With rate limit
config = LLMConfig(endpoint='http://localhost:11434', rate_limit_rpm=60)
backend = OllamaBackend(config)
print(f'Rate limiter initialized: {backend._rate_limiter is not None}')

# Without rate limit (default)
config2 = LLMConfig(endpoint='http://localhost:11434')
backend2 = OllamaBackend(config2)
print(f'No rate limiter: {backend2._rate_limiter is None}')
"
```

---

## Session 3: Add Rate Limit Tests (30 min)

### Subtasks

- [ ] Add tests for rate limiter integration
- [ ] Test blocking behavior with mock time

### Session Prompt

```
I'm implementing Plan 8, Task A2 (Session 3) from docs/plans/plan_8/A2-rate-limiting.md.

Goal: Add tests for rate limiting integration.

Please:
1. Read tests/security/test_rate_limiting.py for existing patterns
2. Add new tests (can be in same file or new tests/unit/test_llm_rate_limiting.py):
   - test_backend_no_rate_limit_by_default: LLMConfig() creates backend without limiter
   - test_backend_with_rate_limit_rpm: Config with rpm creates limiter
   - test_rate_limit_blocks_when_exceeded: Mock time, exceed limit, verify wait behavior

Use unittest.mock to mock time.sleep and verify it's called when rate limited.
```

---

## Done When

- [ ] `LLMConfig` has `rate_limit_rpm` and `rate_limit_concurrent` fields
- [ ] `configs/base.yaml` documents rate limit options
- [ ] `LLMBackend` checks rate limit before requests
- [ ] Tests verify rate limiting works
- [ ] Committed: `Plan 8 A2: Wire rate limiting to LLM backends`
