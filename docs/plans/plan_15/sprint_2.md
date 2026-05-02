# Sprint 2 — Conflicting-File Security Fixes

**Plan:** docs/plans/plan_15/OVERVIEW.md
**Wave:** 2 of 2
**Can run in parallel with:** none — depends on Wave 1 (S4 and S9 both touch middleware.py; S2 and S6 both touch dev.py)
**Must complete before:** nothing — final wave

---

### Agent A: S2 + S6 — `rag_ingest` Path Restriction + `store_text` Hardening

**Complexity:** M
**Estimated time:** 1.5 hours
**Files:**
- `src/mcp_server/tools/dev.py` (MODIFY) — Both fixes in one pass
- `tests/unit/test_mcp_dev_tools.py` (MODIFY) — Tests for both

**Instructions:**
Two changes to `dev.py`:

**S2 fix** — In `rag_ingest()`, change:
```python
validated_path = validate_file_path(path, must_exist=True)
```
to:
```python
validated_path = validate_file_path(path, must_exist=True, allowed_roots=[str(config.paths.vault)])
```

**S6 fix** — In `store_text()`:
1. Add text length limit: `if len(text) > 100_000: return {"status": "error", "error": "Text too large (max 100KB)"}`
2. Add content scanning: `validator = get_validator(); validator.validate_query(text)` — wrap in try/except, return error on injection detection
3. Replace `base_meta.update(metadata)` with allowlisted merge:
```python
ALLOWED_META_KEYS = {"topic", "tags", "author", "date", "notes", "source"}
if metadata:
    safe_meta = {k: v for k, v in metadata.items() if k in ALLOWED_META_KEYS}
    base_meta.update(safe_meta)
```

Add tests:
- `test_rag_ingest_rejects_path_outside_vault`
- `test_store_text_rejects_oversized`
- `test_store_text_filters_metadata_keys`
- `test_store_text_preserves_allowed_metadata`

**Definition of Done:**
- [ ] Path outside vault rejected
- [ ] Text > 100KB rejected
- [ ] Reserved metadata keys dropped
- [ ] Allowed metadata keys preserved
- [ ] Tests passing

---

### Agent B: S4 + S9 — MCP Auth + Rate Limiting + Response Hardening

**Complexity:** L
**Estimated time:** 2.5 hours
**Files:**
- `src/mcp_server/middleware.py` (MODIFY) — Wire auth middleware, wire rate limiter, mask admin key
- `src/tools/video/jobs.py` (MODIFY) — Add max_queue
- `src/mcp_server/tools/video.py` (MODIFY) — Strip paths from responses
- `tests/unit/test_mcp_middleware.py` (MODIFY) — Test auth enforcement
- `tests/unit/test_jobs.py` (MODIFY) — Test queue limit
- `tests/unit/test_mcp_video.py` (MODIFY) — Test path stripping

**Instructions:**

**S4 fix (auth)** — In `_apply_auth()`, after creating the authenticator, register it as actual middleware:
```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)
    api_key = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix("Bearer ")
    if not authenticator.validate_key(api_key):
        from starlette.responses import JSONResponse
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)
```

Read `src/utils/auth.py` first to confirm the `validate_key` method name.

**S9 fixes:**
1. **Admin key masking** — Change `logger.info("Generated admin API key: %s", admin_key)` to `logger.info("Admin API key generated: %s...%s", admin_key[:4], admin_key[-4:])`
2. **Job queue limit** — In `JobManager.__init__`, add `self._max_queue = max_workers * 5` (default 10). In `submit()`, check active count before submitting.
3. **Path stripping** — In `video.py` MCP tool responses, replace `str(result.output_path)` with `result.output_path.name if result.output_path else None`. Same for `source_file`, `audio_path`.

Add tests:
- `test_auth_middleware_rejects_no_key` (may need to mock FastAPI app)
- `test_job_queue_limit_rejects_excess`
- `test_mcp_video_response_no_full_paths`

**Definition of Done:**
- [ ] Auth middleware blocks unauthenticated requests
- [ ] Health endpoints bypass auth
- [ ] Admin key masked in logs
- [ ] Job queue rejects when full
- [ ] MCP responses contain filenames only
- [ ] Tests passing
