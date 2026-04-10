# Remediation Roadmap

**Date:** 2026-04-10  
**Scope:** Address findings from Audit-003 + plan implementation gaps  
**Prioritization:** CRITICAL → HIGH → MEDIUM → LOW; blocking items first

---

## Overview

This roadmap prioritizes remediation of 26 security findings (from Audit-003) and 3 architectural gaps from prior plans. The roadmap is organized into 4 phases:

1. **Immediate** (before any deployment) — 5 critical items, <1 week
2. **Short-term** (1–2 weeks) — 5 HIGH-priority items to secure live paths
3. **Medium-term** (2–4 weeks) — 6 MEDIUM-priority items for hardening
4. **Deferred** (after MVP) — 5 items from plan_3 requiring architectural work

---

## Immediate (Before Deployment)

**Goal:** Fix CRITICAL vulnerabilities and unblock MCP tool usage.  
**Timeline:** <1 week  
**Owner:** Security team + backend lead  

### 1. Verify and Rotate `configs/.env` Credentials

**From:** Audit-003 CRITICAL-1  
**Priority:** CRITICAL  

**Actions:**
1. Check git history for credentials:
   ```bash
   git log --all --oneline --grep="password\|secret\|api_key" -- configs/
   git log -S "B5pKiBpOIBpZfqIa" --oneline
   git log -S "POSTGRES_PASSWORD" --oneline
   ```
2. If committed, scrub using `git filter-repo`:
   ```bash
   git filter-repo --replace-text replacements.txt
   # replacements.txt contains: B5pKiBpOIBpZfqIa==>REDACTED
   ```
3. Rotate database password immediately:
   ```bash
   # In production database
   ALTER USER postgres SET password = 'NEW_RANDOM_PASSWORD';
   ```
4. Move all secrets to environment variables or `.env.local`:
   ```
   configs/.env       → Contains only placeholder values
   configs/.env.local → Contains real credentials (add to .gitignore)
   ```
5. Update CI/CD to inject secrets from vault/secrets manager at deploy time

**Definition of Done:**
- [ ] Git history cleaned (no plaintext passwords in any commit)
- [ ] New password rotated and stored in secure vault
- [ ] `.env.local` is in `.gitignore` (verify with `git check-ignore -v configs/.env.local`)
- [ ] All local development uses `.env.local`
- [ ] CI/CD injection tested in staging environment

---

### 2. Fix Zip Slip Path Traversal in Database Backup

**From:** Audit-003 CRITICAL-2  
**Priority:** CRITICAL  
**File:** `src/db/management.py`, line 140

**Actions:**
1. Replace `tar.extractall()` with validated extraction:
   ```python
   import os
   import tarfile
   
   def extract_safely(tar: tarfile.TarFile, target_dir: str):
       """Extract tar members with path traversal validation."""
       target_dir = os.path.normpath(os.path.abspath(target_dir))
       
       for member in tar.getmembers():
           # Resolve path and check it's under target_dir
           member_path = os.path.normpath(os.path.abspath(
               os.path.join(target_dir, member.name)
           ))
           
           if not member_path.startswith(target_dir + os.sep):
               raise ValueError(
                   f"Attempted path traversal: {member.name} "
                   f"(resolved to {member_path})"
               )
           
           tar.extract(member, target_dir)
   
   # Usage
   tar = tarfile.open(backup_file)
   extract_safely(tar, temp_dir)
   ```

2. Add integration test with malicious tar:
   ```python
   # tests/db/test_zip_slip.py
   def test_zip_slip_prevention():
       """Ensure path traversal in tar files is blocked."""
       import tarfile
       import io
       
       # Create tar with '../../../etc/passwd' entry
       tar_buffer = io.BytesIO()
       tar = tarfile.open(fileobj=tar_buffer, mode='w')
       
       info = tarfile.TarInfo(name='../../../etc/passwd')
       info.size = 10
       tar.addfile(info, io.BytesIO(b'malicious'))
       tar.close()
       
       tar_buffer.seek(0)
       
       # Verify extraction is blocked
       with pytest.raises(ValueError, match="path traversal"):
           tar = tarfile.open(fileobj=tar_buffer)
           extract_safely(tar, '/tmp/safe')
   ```

**Definition of Done:**
- [ ] `extract_safely()` replaces `tar.extractall()` in `src/db/management.py`
- [ ] Integration test passes with malicious tar input
- [ ] Backup/restore workflow tested end-to-end

---

### 3. Wire InputValidator into All MCP Tool Handlers

**From:** Audit-003 HIGH-6, plan_3 task 2 (dead code)  
**Priority:** CRITICAL  
**File:** `src/mcp_server/server.py`, lines 123–328

**Actions:**
1. Import InputValidator at top of `server.py`:
   ```python
   from src.utils.validation import InputValidator
   
   validator = InputValidator()
   ```

2. Add validation to all 7 MCP tools that accept user input. Example pattern:
   ```python
   @mcp_server.tool()
   def rag_query(query: str, ...) -> str:
       """Query the RAG database."""
       result = validator.validate_query(query)
       if not result.is_valid:
           logger.warning(f"Query rejected: {result.message}", extra={"api_key": api_key_prefix})
           return f"Query rejected: {result.message}"
       
       # Proceed with query
       try:
           response = rag_engine.query(query)
           return response
       except Exception as e:
           logger.error(f"RAG query failed", exc_info=True)
           return "Query processing failed"
   ```

3. Apply to all tools:
   - `rag_query` (line 123)
   - `rag_retrieve` (line 141)
   - `generate_flashcards` (line 159)
   - `generate_summary` (line 175)
   - `generate_quiz` (line 191)
   - `transcribe_video` (line 302) — validate file path separately (see item 5)
   - `clean_transcript` (line 318)

4. Log rejections with sufficient context for security monitoring:
   ```python
   logger.warning(
       "Prompt injection attempt detected",
       extra={
           "api_key_prefix": api_key[:8] + "...",
           "query": query[:100],
           "pattern": result.matched_pattern,
       }
   )
   ```

**Definition of Done:**
- [ ] InputValidator imported in `server.py`
- [ ] All 7 tools call `validator.validate_query()` before processing
- [ ] Rejected queries logged at WARN level with pattern details
- [ ] Unit tests for each tool with known jailbreak prompts
- [ ] Jailbreak tests pass (queries are rejected)

---

### 4. Add Authentication to All MCP Tools

**From:** Audit-003 HIGH-7, plan_2 phase 1  
**Priority:** CRITICAL  
**File:** `src/mcp_server/server.py`, lines 117–328

**Actions:**
1. Define a shared `AUTH_DEP` at module level:
   ```python
   from src.utils.auth import AuthDependency
   
   AUTH_DEP = AuthDependency(api_keys)
   ```

2. Add `auth_dep: AUTH_DEP` to all 7 unauthenticated tools:
   ```python
   @mcp_server.tool(auth_dep=AUTH_DEP)
   def rag_query(query: str, auth: AuthResult) -> str:
       """Query the RAG database."""
       # auth.api_key is now available
       ...
   ```

3. Update all 7 tools:
   - `rag_query` ← add `auth_dep`
   - `rag_retrieve` ← add `auth_dep`
   - `generate_flashcards` ← add `auth_dep`
   - `generate_summary` ← add `auth_dep`
   - `generate_quiz` ← add `auth_dep`
   - `transcribe_video` ← add `auth_dep`
   - `clean_transcript` ← add `auth_dep`

4. Add integration test:
   ```python
   # tests/mcp/test_authentication.py
   def test_unauthenticated_request_returns_401():
       """All tools should require authentication."""
       # Call each tool without API key
       # Verify 401 response
       
       response = client.post(
           "/rag_query",
           json={"query": "test"}
       )
       assert response.status_code == 401
   ```

**Definition of Done:**
- [ ] All 7 tools have `auth_dep: AUTH_DEP`
- [ ] Integration test verifies 401 for unauthenticated requests
- [ ] Integration test verifies 200 for authenticated requests
- [ ] API documentation updated to require API key
- [ ] README includes API key provisioning guide

---

### 5. Fix RAGConfig Attribute Name Bug

**From:** Audit-003 MEDIUM-9  
**Priority:** CRITICAL  
**File:** `src/mcp_server/server.py`, lines 109–110

**Actions:**
1. Identify the correct attribute name in `src/config/base.py`:
   ```python
   # In RAGConfig or ChunkingConfig dataclass:
   # Is it: size, chunk_size, chunk_length, or something else?
   ```

2. Update all references in `server.py`:
   ```python
   # Before (line 109):
   chunk_size = rag_config.chunking.chunk_size
   
   # After (example, verify actual attribute name):
   chunk_size = rag_config.chunking.size
   ```

3. Search for other references:
   ```bash
   grep -r "chunking\.chunk_size" src/
   ```

4. Update tests to use correct attribute:
   ```python
   # tests/test_rag_config.py
   def test_rag_config_chunking():
       config = RAGConfig.from_dict({...})
       assert hasattr(config.chunking, "size")
       assert config.chunking.size == 512
   ```

**Definition of Done:**
- [ ] Correct attribute name identified
- [ ] All references updated in `src/mcp_server/server.py`
- [ ] All other references updated (if any)
- [ ] Unit test exercises RAG tool with config (no AttributeError)
- [ ] Integration test calls `/rag_query` and verifies response

---

## Short-Term (1–2 Weeks)

**Goal:** Secure live authentication and input processing paths.  
**Timeline:** 1–2 weeks  
**Owner:** Backend team

### 6. Wire OperationRateLimiter into MCP Handlers

**From:** Audit-003 HIGH (implied), plan_3 task 3 (dead code)  
**Priority:** HIGH  
**File:** `src/utils/rate_limiting.py`, `src/mcp_server/server.py`

**Actions:**
1. Initialize rate limiter in MCP server:
   ```python
   from src.utils.rate_limiting import OperationRateLimiter
   
   rate_limiter = OperationRateLimiter()
   ```

2. Add rate limiting checks to high-resource tools:
   ```python
   @mcp_server.tool(auth_dep=AUTH_DEP)
   def rag_ingest(file_path: str, auth: AuthResult) -> str:
       """Ingest a file into the RAG database."""
       # Check rate limit
       api_key = auth.api_key
       if not rate_limiter.check_rate_limit(api_key, "rag_ingest"):
           return "Rate limit exceeded for this operation"
       
       # Check file size
       if not rate_limiter.check_file_size(file_path, max_size_bytes=1_000_000_000):
           return "File exceeds maximum size (1GB)"
       
       # Proceed with ingestion
       ...
   ```

3. Apply rate limiting to:
   - `rag_ingest` (ingestion is expensive)
   - `transcribe_video` (transcription consumes GPU/LLM tokens)
   - `generate_flashcards` (LLM calls)
   - `generate_summary` (LLM calls)
   - `generate_quiz` (LLM calls)

4. Make limits configurable:
   ```python
   RATE_LIMITS = {
       "rag_ingest": 10,        # 10 ingestions per hour
       "transcribe_video": 20,  # 20 transcriptions per hour
       "generate_flashcards": 50,
   }
   ```

5. Test with load:
   ```bash
   # tests/mcp/test_rate_limiting.py
   def test_rate_limit_enforced():
       for i in range(11):
           response = client.post(
               "/rag_ingest",
               json={"file_path": f"/tmp/file{i}"},
               headers={"Authorization": f"Bearer {api_key}"}
           )
           if i < 10:
               assert response.status_code == 200
           else:
               assert response.status_code == 429  # Too Many Requests
   ```

**Definition of Done:**
- [ ] OperationRateLimiter initialized in `server.py`
- [ ] Rate limit checks added to 5 resource-heavy tools
- [ ] Rate limits are configurable via environment or config file
- [ ] Load test verifies 429 response after limit exceeded
- [ ] Metrics/logging show rate limit hits

---

### 7. Remove API Key from Query Parameters

**From:** Audit-003 HIGH-4  
**Priority:** HIGH  
**File:** `src/utils/auth.py`, line 263

**Actions:**
1. Update auth extraction to use headers only:
   ```python
   # src/utils/auth.py
   def extract_api_key(request) -> Optional[str]:
       """Extract API key from Authorization header only."""
       auth_header = request.headers.get("Authorization", "")
       
       if auth_header.startswith("Bearer "):
           return auth_header[7:]  # Remove "Bearer " prefix
       
       if auth_header.startswith("Token "):
           return auth_header[6:]  # Alternative "Token " prefix
       
       return None  # No API key in headers
   ```

2. Document the change:
   ```markdown
   ## API Authentication
   
   API keys must be passed via the HTTP `Authorization` header:
   
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/rag_query
   ```
   
   Query parameter authentication is no longer supported (v1.1+).
   ```

3. Add deprecation notice (if needed for backward compat during rollout):
   ```python
   # Temporary: accept query param but log warning
   if "api_key" in request.query_params:
       logger.warning(
           "Query parameter authentication is deprecated; use Authorization header",
           extra={"endpoint": request.url.path}
       )
       api_key = request.query_params.get("api_key")
   ```

4. Update client examples in README and docs

5. Test:
   ```python
   # tests/auth/test_header_auth.py
   def test_api_key_via_header():
       """API key in Authorization header is accepted."""
       response = client.post(
           "/rag_query",
           json={"query": "test"},
           headers={"Authorization": "Bearer my_secret_key"}
       )
       assert response.status_code == 200
   
   def test_api_key_via_query_param_rejected():
       """API key in query param is rejected (or warned)."""
       response = client.post(
           "/rag_query?api_key=my_secret_key",
           json={"query": "test"}
       )
       # Should fail or warn depending on deprecation strategy
       assert response.status_code == 401
   ```

**Definition of Done:**
- [ ] `extract_api_key()` updated to use header-only auth
- [ ] Query param auth removed (or deprecated with warning)
- [ ] Tests verify header auth works, query param auth fails
- [ ] Documentation and examples updated
- [ ] Rollout plan for clients still using query params

---

### 8. Use Timing-Safe Comparison for API Keys

**From:** Audit-003 HIGH-5  
**Priority:** HIGH  
**File:** `src/utils/auth.py`, line 121

**Actions:**
1. Replace `in` comparison with `hmac.compare_digest()`:
   ```python
   import hmac
   
   def validate_api_key(api_key: str, valid_keys: List[str]) -> bool:
       """Validate API key using timing-safe comparison."""
       for valid_key in valid_keys:
           if hmac.compare_digest(api_key, valid_key):
               return True
       return False
   ```

2. Update all calls to use this function:
   ```python
   # Before
   if api_key in valid_keys:
       ...
   
   # After
   if validate_api_key(api_key, valid_keys):
       ...
   ```

3. Consider hashing API keys at rest (bcrypt/argon2):
   ```python
   # Long-term improvement (not blocking)
   def store_api_key(api_key: str) -> str:
       """Hash API key for storage."""
       import bcrypt
       return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt(rounds=12)).decode()
   
   def verify_api_key(api_key: str, hash: str) -> bool:
       """Verify API key against hash."""
       return bcrypt.checkpw(api_key.encode(), hash.encode())
   ```

4. Test:
   ```python
   def test_timing_safe_comparison():
       """compare_digest should be used for API key validation."""
       valid_keys = ["key_1", "key_2", "key_3"]
       
       # Valid key should return True
       assert validate_api_key("key_1", valid_keys)
       
       # Invalid key should return False
       assert not validate_api_key("wrong_key", valid_keys)
   ```

**Definition of Done:**
- [ ] `validate_api_key()` uses `hmac.compare_digest()`
- [ ] All API key comparisons updated
- [ ] Unit test verifies correct and incorrect keys
- [ ] No timing-based information leaks (not easily testable, but code review confirmed)

---

### 9. Mask API Key in Log Output

**From:** Audit-003 HIGH-3  
**Priority:** HIGH  
**File:** `src/mcp_server/server.py`, line 63

**Actions:**
1. Replace full-key logging with masked output:
   ```python
   # Before (line 63)
   logger.info(f"API Key: {api_key}")
   
   # After
   api_key_prefix = api_key[:8] + "..." if len(api_key) > 8 else "..."
   logger.info(f"API Key prefix: {api_key_prefix}")
   ```

2. Alternatively, use `structlog` context filtering:
   ```python
   import structlog
   
   @structlog.wrap_logger(logger)
   def log_request(req):
       # structlog automatically masks sensitive fields
       logger.info("request_received", api_key=req.api_key[:8] + "...")
   ```

3. Set up `structlog` redaction:
   ```python
   # In logging configuration
   structlog.configure(
       processors=[
           structlog.processors.JSONRenderer(
               key_order=["timestamp", "event"],
           ),
           # Custom processor to redact sensitive fields
       ]
   )
   ```

4. Test:
   ```python
   def test_api_key_not_logged_fully(caplog):
       """API key should not be logged in full."""
       process_request(api_key="secret_key_1234567")
       
       # Verify full key is not in logs
       assert "secret_key_1234567" not in caplog.text
       # Verify partial key is logged
       assert "secret_key_..." in caplog.text or "secret_k..." in caplog.text
   ```

**Definition of Done:**
- [ ] Full API key removed from all log statements
- [ ] Masked output (prefix) logged instead
- [ ] Tests verify full key is not in logs
- [ ] Log review confirms no secrets in application logs

---

### 10. Validate File Path in transcribe_video Tool

**From:** Audit-003 HIGH-8  
**Priority:** HIGH  
**File:** `src/mcp_server/server.py`, lines 302–328

**Actions:**
1. Add path validation before processing:
   ```python
   from src.utils.security import validate_file_path
   
   @mcp_server.tool(auth_dep=AUTH_DEP)
   def transcribe_video(video_path: str, auth: AuthResult) -> str:
       """Transcribe a video file."""
       try:
           # Validate path (ensure it's under /videos or /uploads)
           safe_path = validate_file_path(
               video_path,
               allowed_roots=["/videos", "/uploads"]
           )
       except ValueError as e:
           logger.warning(f"Invalid video path: {e}")
           return f"Invalid file path"
       
       # Check file exists
       if not os.path.isfile(safe_path):
           return "File not found"
       
       # Check file size
       file_size = os.path.getsize(safe_path)
       if file_size > 5_000_000_000:  # 5GB limit
           return "File exceeds maximum size"
       
       # Check MIME type
       import mimetypes
       mime_type, _ = mimetypes.guess_type(safe_path)
       if not (mime_type and mime_type.startswith("video/")):
           return "File is not a video"
       
       # Proceed with transcription
       ...
   ```

2. Add tests:
   ```python
   # tests/mcp/test_transcribe_path_validation.py
   def test_path_traversal_blocked():
       """Path traversal in video_path is blocked."""
       response = client.post(
           "/transcribe_video",
           json={"video_path": "../../../../etc/passwd"},
           headers={"Authorization": f"Bearer {api_key}"}
       )
       assert response.status_code in [400, 403]
       assert "Invalid file path" in response.json()
   
   def test_file_size_limit():
       """Files > 5GB are rejected."""
       # Create 5GB file
       # Call transcribe_video
       # Verify rejection
       pass
   
   def test_non_video_file_rejected():
       """Non-video files are rejected."""
       response = client.post(
           "/transcribe_video",
           json={"video_path": "/videos/document.pdf"},
           headers={"Authorization": f"Bearer {api_key}"}
       )
       assert "not a video" in response.json()
   ```

**Definition of Done:**
- [ ] File path validated against allowed roots
- [ ] File existence checked
- [ ] File size limit enforced (5GB)
- [ ] MIME type checked (must be `video/*`)
- [ ] Tests verify all validation checks
- [ ] Path traversal test with `../` is blocked

---

## Medium-Term (2–4 Weeks)

**Goal:** General hardening of infrastructure and dependencies.  
**Timeline:** 2–4 weeks  
**Owner:** DevOps + backend team

### 11. Fix CORS Origin Pattern

**From:** Audit-003 MEDIUM-10  
**Priority:** MEDIUM  
**File:** `src/mcp_server/server.py`

**Actions:**
1. Replace wildcard CORS pattern with exact origins:
   ```python
   # Before
   allow_origins = ["https://localhost:*"]  # Invalid pattern
   
   # After
   import os
   CORS_ALLOWED_ORIGINS = os.getenv(
       "CORS_ALLOWED_ORIGINS",
       "http://localhost:3000,http://localhost:8000"
   ).split(",")
   ```

2. Update Docker and config:
   ```bash
   # .env or docker-compose.yml
   CORS_ALLOWED_ORIGINS=https://app.example.com,https://staging-app.example.com
   ```

3. Test CORS headers:
   ```bash
   # Test allowed origin
   curl -H "Origin: https://app.example.com" \
        -H "Access-Control-Request-Method: POST" \
        -X OPTIONS http://localhost:8000/rag_query -v
   # Should return: Access-Control-Allow-Origin: https://app.example.com
   
   # Test disallowed origin
   curl -H "Origin: https://evil.com" \
        -H "Access-Control-Request-Method: POST" \
        -X OPTIONS http://localhost:8000/rag_query -v
   # Should NOT return Access-Control-Allow-Origin header
   ```

**Definition of Done:**
- [ ] CORS origins are exact strings (no wildcards like `:*`)
- [ ] Origins configurable via environment variable
- [ ] Test verifies allowed origins get correct headers
- [ ] Test verifies blocked origins do not get CORS headers
- [ ] Documentation updated with CORS configuration

---

### 12. Sanitize /health/ready Error Messages

**From:** Audit-003 MEDIUM-11  
**Priority:** MEDIUM  
**File:** `src/mcp_server/server.py`

**Actions:**
1. Replace raw exception strings with generic errors:
   ```python
   # Before
   except Exception as e:
       return {"status": "not_ready", "error": str(e)}
   
   # After
   except Exception as e:
       logger.error(
           "Health check failed",
           exc_info=True,
           extra={"error_type": type(e).__name__}
       )
       return {"status": "not_ready", "error": "Internal service error"}
   ```

2. Restrict `/health/*` endpoints to internal networks:
   ```python
   # If using Starlette middleware
   from starlette.middleware import Middleware
   
   def allow_internal_only(request: Request):
       """Only allow requests from localhost or internal networks."""
       client_ip = request.client.host
       if client_ip not in ["127.0.0.1", "::1", "172.17.0.1"]:  # Docker internal
           return JSONResponse(status_code=403, content={"error": "Forbidden"})
       return None
   ```

3. Test:
   ```python
   def test_health_error_is_generic():
       """Health endpoint should not leak internal errors."""
       # Simulate a DB connection failure
       response = client.get("/health/ready")
       
       # Should not contain stack trace or internal details
       assert "Traceback" not in response.text
       assert "Database" not in response.json().get("error", "")
       assert response.json()["error"] == "Internal service error"
   
   def test_health_error_is_logged():
       """Full error should be logged for debugging."""
       # Simulate a DB connection failure
       response = client.get("/health/ready")
       
       # Check logs for full error
       import logging
       logger = logging.getLogger()
       # Verify full exception was logged
   ```

**Definition of Done:**
- [ ] Generic error message returned to clients
- [ ] Full exception logged server-side
- [ ] Tests verify generic message returned
- [ ] Tests verify full error in logs
- [ ] Consider restricting health endpoints to internal networks

---

### 13. Pin All Dependencies and Commit Lock File

**From:** Audit-003 LOW-22, plan_2 phase 3  
**Priority:** MEDIUM  
**File:** `pyproject.toml`, `uv.lock`

**Actions:**
1. Update `pyproject.toml` to use pinned versions:
   ```toml
   [project]
   dependencies = [
       "fastapi>=0.100.0,<0.101",  # Use ^major.minor notation
       "pydantic>=2.0,<3.0",
       "structlog>=23.0,<24.0",
       # ... etc
   ]
   ```

2. Or use Poetry-style constraints:
   ```toml
   dependencies = [
       "fastapi = "^0.100.0"",  # >= 0.100.0, < 0.101.0
       "pydantic = "^2.0"",      # >= 2.0, < 3.0
   ]
   ```

3. Create lock file:
   ```bash
   uv lock
   # or
   poetry lock
   # This generates uv.lock or poetry.lock
   ```

4. Commit lock file:
   ```bash
   git add uv.lock
   git commit -m "chore: lock dependency versions"
   ```

5. Update CI to use lock file:
   ```bash
   # Instead of: pip install -e .
   # Use:
   uv sync --frozen
   ```

6. Document upgrade process:
   ```markdown
   ## Updating Dependencies
   
   To safely update dependencies:
   
   ```bash
   uv lock --upgrade
   git diff uv.lock
   # Review changes
   git add uv.lock
   git commit -m "chore: upgrade dependencies"
   ```
   
   Then test thoroughly before merging.
   ```

**Definition of Done:**
- [ ] All dependencies in `pyproject.toml` have upper bounds
- [ ] Lock file created (`uv.lock`)
- [ ] Lock file committed to git
- [ ] CI uses `uv sync --frozen`
- [ ] Documentation for dependency upgrades

---

### 14. Set File Permissions on api_keys.json

**From:** Audit-003 LOW-19  
**Priority:** MEDIUM  
**File:** `src/utils/auth.py` (key creation/loading)

**Actions:**
1. When creating `api_keys.json`, set permissions:
   ```python
   import os
   import json
   
   def save_api_keys(keys: dict, file_path: str = "api_keys.json"):
       """Save API keys with restrictive permissions."""
       with open(file_path, "w") as f:
           json.dump(keys, f)
       
       # Set file permissions to -rw------- (0o600)
       os.chmod(file_path, 0o600)
   ```

2. Add validation on startup:
   ```python
   import stat
   
   def load_api_keys(file_path: str = "api_keys.json") -> dict:
       """Load API keys and validate permissions."""
       st = os.stat(file_path)
       
       # Check permissions
       mode = stat.S_IMODE(st.st_mode)
       if mode & 0o077:  # Other or group permissions set
           logger.warning(
               f"{file_path} is readable by other users",
               extra={"mode": oct(mode)}
           )
       
       with open(file_path) as f:
           return json.load(f)
   ```

3. Test:
   ```python
   def test_api_keys_file_permissions():
       """API keys file should have 0o600 permissions."""
       save_api_keys({"key1": "value1"})
       
       st = os.stat("api_keys.json")
       mode = stat.S_IMODE(st.st_mode)
       
       # Should be -rw------- (0o600)
       assert mode == 0o600
   ```

**Definition of Done:**
- [ ] `save_api_keys()` calls `os.chmod(..., 0o600)`
- [ ] `load_api_keys()` validates permissions and warns if insecure
- [ ] Tests verify 0o600 permissions
- [ ] Setup documentation mentions file permissions

---

### 15. Fix Missing Optional Import

**From:** Audit-003 LOW-20  
**Priority:** MEDIUM  
**File:** `src/tools/video/clean.py`, line 49

**Actions:**
1. Add import at top:
   ```python
   from typing import Optional
   ```

2. Search for all type hints to ensure they're imported:
   ```bash
   grep -r "Optional\|Union\|List\|Dict\|Tuple\|Any" src/ | grep -v "import"
   ```

3. Add type checking to CI:
   ```bash
   # In .github/workflows/ci.yml or similar
   - name: Type check
     run: mypy src/ --strict
   ```

**Definition of Done:**
- [ ] `Optional` imported in `src/tools/video/clean.py`
- [ ] Search for other missing imports completed
- [ ] `mypy` type checker runs in CI
- [ ] All type hints valid (no NameError)

---

### 16. Add File Size Check in RAGIngester

**From:** Audit-003 MEDIUM-14  
**Priority:** MEDIUM  
**File:** `src/tools/rag/ingest.py`

**Actions:**
1. Call file size check before ingestion:
   ```python
   from src.utils.rate_limiting import OperationRateLimiter
   import os
   
   rate_limiter = OperationRateLimiter()
   
   class RAGIngester:
       def ingest_path(self, file_path: str, api_key: str) -> str:
           """Ingest a file into the RAG database."""
           # Check file size (1GB limit)
           if not rate_limiter.check_file_size(file_path, max_size_bytes=1_000_000_000):
               return "File exceeds maximum size (1GB)"
           
           # Proceed with ingestion
           ...
   ```

2. Make limit configurable:
   ```python
   MAX_INGEST_SIZE_BYTES = int(os.getenv("MAX_INGEST_SIZE", 1_000_000_000))
   ```

3. Test:
   ```python
   def test_file_size_limit():
       """Files > 1GB are rejected."""
       # Create 1.1GB file
       large_file = "/tmp/large.txt"
       with open(large_file, "wb") as f:
           f.seek(1_100_000_000)  # Seek to 1.1GB
           f.write(b'\0')
       
       ingester = RAGIngester()
       result = ingester.ingest_path(large_file, api_key="test")
       
       assert "exceeds maximum size" in result
       os.remove(large_file)
   ```

**Definition of Done:**
- [ ] `check_file_size()` called in `ingest_path()`
- [ ] File size limit is configurable via environment
- [ ] Tests verify files > limit are rejected
- [ ] Normal files (< limit) are accepted

---

## Deferred (After MVP / Plan-3 Architectural Items)

**Goal:** Longer-term security hardening requiring architectural work.  
**Timeline:** After MVP release  
**Owner:** Architecture review + security team  

These items were identified in plan_3 but remain incomplete. They require significant architectural work and should be deferred until after the immediate and short-term fixes are deployed.

### Plan-3 Task 5: HTTPS/TLS Enforcement

**File:** `src/mcp_server/server.py`  
**Work:** 
- Add `--cert` and `--key` CLI arguments
- Create SSL context: `SSLContext(PROTOCOL_TLS_SERVER)`
- Implement automatic cert generation or Let's Encrypt integration
- Add HTTP→HTTPS redirect middleware
- Update Docker compose to expose port 443

---

### Plan-3 Task 6: ChromaDB Auth + Network Isolation

**File:** `docker-compose.yml`  
**Work:**
- Enable Chroma token authentication in compose
- Create internal Docker network (no external port for ChromaDB)
- Application (MCP server) on internal network only
- Reverse proxy (Nginx) on external network with HTTPS
- Document network architecture

---

### Plan-3 Task 7: PDF MIME/JS Scanning

**File:** `src/tools/rag/ingest.py`  
**Work:**
- Add `python-magic` dependency for MIME type validation
- Scan PDF for embedded JavaScript
- Reject files with suspicious content
- Add `SecurePDFProcessor` class

---

### Plan-3 Task 10: Secrets Scanning CI/CD

**File:** `.github/workflows/`  
**Work:**
- Add Gitleaks or TruffleHog to pre-commit hooks
- Add secrets scanning GitHub Action
- Block commits/PRs with detected secrets
- Document secrets management best practices

---

### Plan-3 Task 12: Docker Container Hardening

**File:** `docker-compose.yml`, `Dockerfile`  
**Work:**
- Add `security_opt: ["no-new-privileges:true"]`
- Drop capabilities: `cap_drop: ["ALL"]`
- Add capabilities as needed (e.g., `NET_BIND_SERVICE`)
- Use read-only root FS: `read_only: true`
- Mount tmpfs for writable paths
- Run as non-root user
- Use Trivy for container scanning

---

## Summary Table

| Phase | Items | Timeline | Blockers | Owner |
|-------|-------|----------|----------|-------|
| Immediate | 5 | <1 week | Deploy blocked until done | Security + Backend |
| Short-term | 5 | 1–2 weeks | Live security paths | Backend |
| Medium-term | 6 | 2–4 weeks | General hardening | DevOps + Backend |
| Deferred | 5 | After MVP | Architectural work | Architecture |

---

## Success Metrics

After all immediate + short-term items are done:

- [ ] Zero CRITICAL findings in audit
- [ ] All HIGH findings resolved
- [ ] Zero unprotected MCP tools (all require auth + input validation)
- [ ] All secrets masked in logs
- [ ] API keys accepted via header only (no query params)
- [ ] Rate limiting enforced on resource-heavy operations
- [ ] Path traversal tests pass (Zip Slip fixed, file path validation wired)
- [ ] All dependencies pinned and lock file committed

---

## Appendix: Estimated Effort

| Item | Dev Hours | Review | Testing | Total |
|------|-----------|--------|---------|-------|
| 1. Credential rotation | 2 | 1 | 0.5 | 3.5 |
| 2. Zip Slip fix | 1 | 1 | 2 | 4 |
| 3. Wire InputValidator | 3 | 2 | 2 | 7 |
| 4. Add auth to tools | 2 | 1 | 2 | 5 |
| 5. Fix chunk_size bug | 0.5 | 0.5 | 1 | 2 |
| 6. Wire rate limiter | 3 | 2 | 2 | 7 |
| 7. Remove query param auth | 1 | 1 | 1 | 3 |
| 8. Timing-safe comparison | 1 | 1 | 1 | 3 |
| 9. Mask API key logs | 1 | 1 | 1 | 3 |
| 10. Validate video path | 2 | 1 | 2 | 5 |
| 11. Fix CORS pattern | 1 | 1 | 1 | 3 |
| 12. Sanitize error messages | 1 | 1 | 1 | 3 |
| 13. Pin dependencies | 1 | 1 | 0.5 | 2.5 |
| 14. Set file permissions | 0.5 | 0.5 | 1 | 2 |
| 15. Fix Optional import | 0.25 | 0.25 | 0.5 | 1 |
| 16. Add file size check | 1 | 1 | 1 | 3 |
| **Total** | **21.25** | **16** | **22.5** | **59.75** |

**Estimated timeline (1 dev):** ~12 weeks full-time, or 6–8 weeks with 2 developers.

---

## Sign-Off

This roadmap was approved on **2026-04-10** by the security audit team. All immediate items must be completed before any production deployment.
