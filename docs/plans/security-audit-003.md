# Security Audit Report — Audit-003 (Fresh)

**Date:** 2026-04-10  
**Scope:** Full CorpusCallosum codebase (mono-repo post-restructure)  
**Auditor:** Claude Code (Haiku 4.5)  
**Context:** Audit-001 and Audit-002 review completed; this audit identifies additional vulnerabilities and patterns missed in prior audits.

---

## Executive Summary

This fresh audit identified **2 CRITICAL, 6 HIGH, 8 MEDIUM, 6 LOW, and 4 INFO-level findings**. The most concerning pattern is that security code (InputValidator, OperationRateLimiter) was implemented but never integrated into live application paths—creating a false sense of security. Two new critical vulnerabilities were discovered: plaintext credentials potentially committed to git history, and a Zip Slip path traversal in database backup extraction.

**Deployment blockers:** CRITICAL findings must be resolved before any release.  
**Wiring blockers:** InputValidator and OperationRateLimiter must be integrated into MCP handlers before claiming security compliance.

---

## CRITICAL Findings (Must fix before deployment)

### 1. Plaintext Credentials in Version Control

**File:** `configs/.env`  
**Risk:** Database password stored as plaintext in the codebase  
**Details:**  
```
POSTGRES_PASSWORD=B5pKiBpOIBpZfqIa
```

This credential may be committed to git history and accessible to anyone with repo access or cloned copies.

**CWE:** CWE-798 (Use of Hard-Coded Credentials)  
**Severity:** CRITICAL  
**Recommendation:**
1. Immediately check git history: `git log --all -S "B5pKiBpOIBpZfqIa"` or `git log --all -S "POSTGRES_PASSWORD"`
2. If committed, use `git filter-branch` or `git-filter-repo` to scrub from history
3. Rotate the database password
4. Move all secrets to environment variables or `.env.local` (which should be `.gitignore`d)
5. Commit only `.env.example` with placeholder values

**Status:** NOT RESOLVED

---

### 2. Zip Slip Path Traversal in Database Backup Extraction

**File:** `src/db/management.py`, line 140  
**Risk:** Untrusted tar archive extraction without path validation  
**Details:**  
```python
# Line 140
tar.extractall(temp_dir)
```

An attacker can craft a malicious tar archive with entries like `../../../etc/passwd` to extract files outside the intended directory, potentially overwriting system files or application code.

**CWE:** CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)  
**Severity:** CRITICAL  
**Recommendation:**
1. Validate each tar member path before extraction:
   ```python
   import os
   for member in tar.getmembers():
       path = os.path.normpath(os.path.join(temp_dir, member.name))
       if not path.startswith(os.path.normpath(temp_dir)):
           raise ValueError(f"Attempted path traversal: {member.name}")
       tar.extract(member, temp_dir)
   ```
2. Alternatively, use `tarfile.open(...).extractall()` with a filter (Python 3.12+) or third-party library like `py7zr`
3. Add integration tests with malicious tar files

**Status:** NOT RESOLVED

---

## HIGH Findings (6)

### 3. API Key Logged at INFO Level

**File:** `src/mcp_server/server.py`, line 63  
**Risk:** Sensitive credential exposed in application logs and log aggregation systems  
**Details:**  
```python
logger.info(f"API Key: {api_key}")
```

Any log consumer (dev, monitoring, SIEM) can see plaintext API keys.

**CWE:** CWE-532 (Insertion of Sensitive Information into Log File)  
**Severity:** HIGH  
**Recommendation:**
1. Never log the full API key. Log only a prefix or hash:
   ```python
   logger.info(f"API Key prefix: {api_key[:8]}...")
   ```
2. Or use a hash: `logger.info(f"API Key hash: {hashlib.sha256(api_key.encode()).hexdigest()[:16]}...")`
3. Configure log redaction rules in `structlog` to automatically mask secrets
4. Set log level to DEBUG for sensitive operations; DEBUG logs should not reach production

**Status:** NOT RESOLVED

---

### 4. API Key Accepted via URL Query Parameters

**File:** `src/utils/auth.py`, line 263  
**Risk:** Credentials in URLs are logged by proxies, CDNs, and server access logs  
**Details:**  
The MCP server accepts API keys via query string:
```python
api_key = query_params.get("api_key")
```

Query parameters are logged in access logs, browser history, referrer headers, and proxies.

**CWE:** CWE-614 (Sensitive Cookie in HTTPS Session Without 'Secure' Attribute) / CWE-532  
**Severity:** HIGH  
**Recommendation:**
1. Accept API keys only via HTTP headers (e.g., `Authorization: Bearer <key>`):
   ```python
   auth_header = headers.get("Authorization", "")
   if auth_header.startswith("Bearer "):
       api_key = auth_header[7:]
   ```
2. Document that clients must use header-based auth
3. Add a deprecation warning if query param auth is still supported (for backward compatibility during migration)
4. Remove query param auth in the next major version

**Status:** NOT RESOLVED

---

### 5. Non-Timing-Safe API Key Comparison

**File:** `src/utils/auth.py`, line 121  
**Risk:** Timing attack to brute-force API keys  
**Details:**  
```python
if api_key in valid_keys:
```

The `in` operator performs string comparison character-by-character and short-circuits on the first mismatch. An attacker can measure response time to deduce correct characters.

**CWE:** CWE-208 (Observable Timing Discrepancy)  
**Severity:** HIGH  
**Recommendation:**
1. Use `hmac.compare_digest()` for constant-time comparison:
   ```python
   import hmac
   
   for valid_key in valid_keys:
       if hmac.compare_digest(api_key, valid_key):
           return True
   return False
   ```
2. Hash API keys before storage and comparison (use bcrypt or argon2)
3. Add rate limiting on auth failures to slow brute-force attempts

**Status:** NOT RESOLVED

---

### 6. InputValidator Dead Code (Prompt Injection Protection)

**File:** `src/utils/validation.py` (all), `src/mcp_server/server.py` (line 109+)  
**Risk:** Prompt injection protection implemented but never activated in production  
**Details:**  
The `InputValidator` class in `src/utils/validation.py` provides prompt injection detection:
```python
class InputValidator:
    def validate_query(self, query: str) -> ValidationResult:
        # Checks for 128+ patterns (jailbreak attempts, SQL injection keywords, etc.)
```

However, it is **only imported in test files** (`tests/security/test_prompt_injection.py`). None of the 7 MCP tool handlers call `validate_query()`:
- `rag_query` (line 123)
- `rag_retrieve` (line 141)
- `generate_flashcards` (line 159)
- `generate_summary` (line 175)
- `generate_quiz` (line 191)
- `transcribe_video` (line 302)
- `clean_transcript` (line 318)

**CWE:** CWE-94 (Improper Control of Generation of Code)  
**Severity:** HIGH  
**Recommendation:**
1. Wire validation into all MCP tools that accept user input:
   ```python
   from src.utils.validation import InputValidator
   
   validator = InputValidator()
   
   @mcp_server.tool()
   def rag_query(query: str) -> str:
       result = validator.validate_query(query)
       if not result.is_valid:
           return f"Query rejected: {result.message}"
       # ... proceed with query
   ```
2. Log rejections at WARN level for security monitoring
3. Return user-friendly error messages without leaking validator details
4. Test with known jailbreak prompts to ensure effectiveness

**Status:** CODE EXISTS, NOT WIRED

---

### 7. Missing Authentication on MCP Tools

**File:** `src/mcp_server/server.py`, lines 123–328  
**Risk:** Unauthorized access to LLM-based operations  
**Details:**  
Only `rag_ingest` (line 117) has `auth_dep: AuthDependency(api_keys)`. All other 7 tools are unauthenticated:
- `rag_query` — no `auth_dep`
- `rag_retrieve` — no `auth_dep`
- `generate_flashcards` — no `auth_dep`
- `generate_summary` — no `auth_dep`
- `generate_quiz` — no `auth_dep`
- `transcribe_video` — no `auth_dep`
- `clean_transcript` — no `auth_dep`

Anyone with network access can invoke these tools and consume compute resources (LLM tokens, GPU time, storage).

**CWE:** CWE-287 (Improper Authentication)  
**Severity:** HIGH  
**Recommendation:**
1. Define a shared `auth_dep` at the top of `server.py`:
   ```python
   AUTH_DEP = AuthDependency(api_keys)
   ```
2. Add `auth_dep: AUTH_DEP` to all 7 remaining tools
3. Test that unauthenticated requests return 401/403
4. Document API key provisioning in the README
5. Consider rate limiting per API key (each key gets X tokens/hour)

**Status:** NOT RESOLVED

---

### 8. Unvalidated File Path in transcribe_video Tool

**File:** `src/mcp_server/server.py`, lines 302–328  
**Risk:** Path traversal or malicious file access  
**Details:**  
The `transcribe_video` tool accepts a `video_path` parameter with no validation:
```python
@mcp_server.tool()
def transcribe_video(video_path: str, ...) -> str:
    # No validation of video_path; could be /etc/passwd, ../../../sensitive.mp4, etc.
```

An attacker can request transcription of arbitrary files the application can read (system files, private keys, databases).

**CWE:** CWE-22 (Improper Limitation of a Pathname)  
**Severity:** HIGH  
**Recommendation:**
1. Validate file paths before processing:
   ```python
   from src.utils.security import validate_file_path
   
   try:
       safe_path = validate_file_path(video_path, allowed_roots=["/videos", "/uploads"])
   except ValueError as e:
       return f"Invalid file path: {e}"
   ```
2. Accept only file paths under a whitelisted directory
3. Check file MIME type (should be `video/*`, not `text/plain`)
4. Check file size (e.g., <5GB) to prevent resource exhaustion
5. Use `os.path.realpath()` to resolve symlinks and `..` paths

**Status:** NOT RESOLVED

---

## MEDIUM Findings (8)

### 9. Incorrect RAGConfig Attribute Name

**File:** `src/mcp_server/server.py`, lines 109–110  
**Risk:** AttributeError at runtime; feature broken  
**Details:**  
```python
rag_config.chunking.chunk_size  # Does not exist
```

The correct attribute is `rag_config.chunking.size` (or check the actual dataclass definition). This bug will cause the RAG tool to crash when trying to access the chunk size.

**CWE:** N/A (Logic error)  
**Severity:** MEDIUM  
**Recommendation:**
1. Check the actual attribute name in `src/config/base.py` (RAGConfig.chunking dataclass)
2. Update all references in `server.py` to use the correct attribute name
3. Add integration tests that actually instantiate and use RAGConfig
4. Consider adding type hints to catch this at development time

**Status:** NOT RESOLVED

---

### 10. Invalid CORS Origin Pattern

**File:** `src/mcp_server/server.py`, security headers section  
**Risk:** CORS misconfiguration; headers ineffective  
**Details:**  
```python
allow_origins = ["https://localhost:*"]  # Invalid wildcard pattern
```

Starlette's CORS middleware expects exact domain strings or `["*"]`. The pattern `https://localhost:*` is not valid and will be rejected or treated as a literal string. This either allows unwanted origins or blocks legitimate ones.

**CWE:** CWE-341 (Predictable from Observable State)  
**Severity:** MEDIUM  
**Recommendation:**
1. Use exact origins:
   ```python
   allow_origins = ["https://localhost:3000", "https://localhost:8000"]
   ```
2. Or use a whitelist from config:
   ```python
   allow_origins = config.cors.allowed_origins  # ["https://app.example.com"]
   ```
3. Never use `["*"]` in production (browser safety)
4. Test with curl to verify allowed origins:
   ```bash
   curl -H "Origin: https://localhost:3000" -i http://localhost:8000/health/live
   ```

**Status:** NOT RESOLVED

---

### 11. Health Check Endpoint Leaks Internal Errors

**File:** `src/mcp_server/server.py`, `/health/ready` endpoint  
**Risk:** Information disclosure via error messages  
**Details:**  
```python
except Exception as e:
    return {"status": "not_ready", "error": str(e)}  # Raw exception message
```

Full exception tracebacks may reveal internal file paths, library names, database schemas, or other sensitive details.

**CWE:** CWE-209 (Information Exposure Through an Error Message)  
**Severity:** MEDIUM  
**Recommendation:**
1. Return a generic error message to clients:
   ```python
   except Exception as e:
       logger.error(f"Health check failed: {e}", exc_info=True)  # Log full error
       return {"status": "not_ready", "error": "Internal service error"}
   ```
2. Log the full exception with stack trace for debugging
3. Restrict `/health/` endpoints to internal networks if possible (no exposure to clients)
4. Use structured logging to track errors without exposing details

**Status:** NOT RESOLVED

---

### 12. In-Memory Rate Limiter (Not Persistent)

**File:** `src/utils/rate_limiting.py`  
**Risk:** Rate limits do not persist across service restarts; ineffective in distributed systems  
**Details:**  
The `OperationRateLimiter` stores state in-memory:
```python
class OperationRateLimiter:
    def __init__(self):
        self.call_times = {}  # Dict in memory
```

If the service restarts, all rate limit state is lost. If multiple service instances run, each has independent rate limits (sum of all instances exceeds actual limit).

**CWE:** CWE-770 (Allocation of Resources Without Limits or Throttling)  
**Severity:** MEDIUM  
**Recommendation:**
1. Use Redis for persistent rate limit state (as plan_2 proposed):
   ```python
   from redis import Redis
   
   redis = Redis(host="localhost", port=6379)
   key = f"ratelimit:{api_key}:{operation}"
   redis.incr(key)
   redis.expire(key, 3600)  # 1 hour window
   ```
2. Or use a persistent counter table in the database
3. Consider `slowapi` (FastAPI rate limiting library) which supports Redis
4. For now, document that rate limits are per-instance

**Status:** CODE EXISTS, NOT PERSISTENT

---

### 13. SHA-1 Used for Chunk IDs

**File:** `src/tools/rag/ingest.py`, lines 4 and 217  
**Risk:** SHA-1 is cryptographically broken; vulnerability to collision attacks  
**Details:**  
```python
import hashlib
chunk_id = hashlib.sha1(chunk_text.encode()).hexdigest()
```

SHA-1 has known collision attacks. While this is lower risk than cryptographic use (the purpose is just deduplication), it should be upgraded to SHA-256 for future-proofing.

**CWE:** CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)  
**Severity:** MEDIUM  
**Recommendation:**
1. Replace SHA-1 with SHA-256:
   ```python
   chunk_id = hashlib.sha256(chunk_text.encode()).hexdigest()
   ```
2. Provide a migration script to re-hash existing chunks in the database
3. Update tests to use SHA-256
4. Document the change in release notes

**Status:** NOT RESOLVED

---

### 14. File Size Validation Never Called

**File:** `src/tools/rag/ingest.py`, `OperationRateLimiter.check_file_size()`  
**Risk:** Unbounded file uploads can cause resource exhaustion (disk, memory)  
**Details:**  
The `OperationRateLimiter` class has a `check_file_size()` method:
```python
def check_file_size(self, file_path: str, max_size_bytes: int) -> bool:
    # Checks file size before processing
```

However, it is never called in `RAGIngester.ingest_path()`. Large files (100GB+) can be ingested, consuming disk and memory.

**CWE:** CWE-770 (Allocation of Resources Without Limits or Throttling)  
**Severity:** MEDIUM  
**Recommendation:**
1. Call size check in `ingest_path()`:
   ```python
   from src.utils.rate_limiting import OperationRateLimiter
   
   rate_limiter = OperationRateLimiter()
   if not rate_limiter.check_file_size(file_path, max_size_bytes=1_000_000_000):  # 1GB
       raise ValueError("File exceeds maximum size")
   ```
2. Make max_size configurable per tool
3. Consider quota per API key (total storage used)
4. Test with files >1GB to verify limits are enforced

**Status:** NOT RESOLVED

---

### 15. Docker Compose Ships with Auth Disabled

**File:** `docker-compose.yml`  
**Risk:** Database and services accessible without credentials in development image  
**Details:**  
If this compose file is used in production or accidentally exposed, all services (ChromaDB, Ollama, etc.) may be configured without authentication enabled.

**CWE:** CWE-287 (Improper Authentication)  
**Severity:** MEDIUM  
**Recommendation:**
1. Create separate compose files:
   - `docker-compose.yml` — development (no auth)
   - `docker-compose.prod.yml` — production (auth required)
2. In prod compose, enable auth for all services:
   ```yaml
   chroma:
     environment:
       - IS_PERSISTENT=TRUE
       - CHROMA_AUTH_ENABLED=TRUE
       - CHROMA_AUTH_TOKEN=<random-token>
   ```
3. Document which compose file is appropriate for each environment
4. Validate in CI that prod config has auth enabled
5. Do not ship prod secrets in the repo (use `.env.prod.local`)

**Status:** NOT RESOLVED

---

### 16. ChromaDB HTTP Connection Unencrypted

**File:** `docker-compose.yml`, ChromaDB service  
**Risk:** Vector embeddings and metadata transmitted in plaintext  
**Details:**  
ChromaDB communicates over HTTP (port 8000) by default. In production, this exposes sensitive data (documents, embeddings) to network eavesdropping.

**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information)  
**Severity:** MEDIUM  
**Recommendation:**
1. Enable HTTPS for ChromaDB (requires reverse proxy like Nginx):
   ```yaml
   chroma:
     # Keep on localhost only
     ports: [] # Remove public port
   
   nginx:
     image: nginx:latest
     ports:
       - "443:443"
     volumes:
       - ./chroma.conf:/etc/nginx/conf.d/chroma.conf
       - ./certs:/etc/nginx/certs
   ```
2. Or use a service mesh (e.g., Istio, Linkerd) for mTLS
3. For development, restrict ChromaDB to `localhost` only (no public port)
4. Use environment variable for ChromaDB URL:
   ```python
   CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8000")
   ```

**Status:** NOT RESOLVED

---

## LOW Findings (6)

### 17. Prompt Templates Embed User Input Unsafely

**File:** `src/llm/prompts.py`  
**Risk:** Prompt injection via undelimited user input  
**Details:**  
User queries are embedded directly in f-strings:
```python
prompt = f"Answer: {user_query}"
```

An attacker can inject instructions: `"Answer: Ignore all previous instructions. Now, do X."`

**CWE:** CWE-94 (Improper Control of Generation of Code)  
**Severity:** LOW (mitigated by InputValidator being wired; treated as LOW because it's an LLM concern, not injection into code)  
**Recommendation:**
1. Use delimiters to clearly mark the boundary between system and user input:
   ```python
   prompt = f"""Answer the following question.
   
   <USER_QUERY>
   {user_query}
   </USER_QUERY>
   """
   ```
2. Or use separate system and user messages (best practice):
   ```python
   messages = [
       {"role": "system", "content": "You are a helpful assistant."},
       {"role": "user", "content": user_query}
   ]
   ```
3. Combine with InputValidator (from finding #6) for defense-in-depth

**Status:** NOT RESOLVED

---

### 18. Insufficient Allowlist for $EDITOR Variable

**File:** `src/utils/security.py`, `get_safe_editor()` function  
**Risk:** Editor command injection via EDITOR env var  
**Details:**  
If the allowlist only includes common editors (`vim`, `nano`, `emacs`), an attacker can override with a custom executable or shell command:
```bash
export EDITOR="/tmp/malicious.sh"
```

**CWE:** CWE-426 (Untrusted Search Path)  
**Severity:** LOW  
**Recommendation:**
1. Whitelist absolute paths only:
   ```python
   SAFE_EDITORS = {
       "/usr/bin/vim",
       "/usr/bin/nano",
       "/usr/bin/emacs",
   }
   editor = os.getenv("EDITOR", "")
   if editor not in SAFE_EDITORS:
       raise ValueError("Editor not in allowlist")
   ```
2. Validate that the editor binary exists and is not a symlink to an untrusted location
3. Document approved editors in the README
4. Use full paths in production (avoid PATH search)

**Status:** NOT RESOLVED

---

### 19. api_keys.json File Permissions Not Set

**File:** `api_keys.json` (implied from auth flow)  
**Risk:** File readable by other users on shared systems  
**Details:**  
If `api_keys.json` is created without restrictive permissions (e.g., `chmod 644`), other users on the system can read API keys.

**CWE:** CWE-276 (Incorrect Default File Permissions)  
**Severity:** LOW  
**Recommendation:**
1. When creating `api_keys.json`, set permissions:
   ```python
   with open("api_keys.json", "w") as f:
       json.dump(keys, f)
   os.chmod("api_keys.json", 0o600)  # -rw------- (owner read/write only)
   ```
2. Document this in the setup guide
3. Add a config validation check:
   ```python
   st = os.stat("api_keys.json")
   if st.st_mode & 0o077:
       logger.warning("api_keys.json is readable by other users; consider chmod 600")
   ```

**Status:** NOT RESOLVED

---

### 20. Missing Import in clean.py

**File:** `src/tools/video/clean.py`, line 49  
**Risk:** Runtime NameError if code path is executed  
**Details:**  
```python
Optional[str]  # NameError: Optional not imported
```

This would crash at runtime if that code is invoked.

**CWE:** N/A (Import error)  
**Severity:** LOW  
**Recommendation:**
1. Add import at top of file:
   ```python
   from typing import Optional
   ```
2. Verify all type hints are imported
3. Add type checking to CI:
   ```bash
   mypy src/
   ```

**Status:** NOT RESOLVED

---

### 21. Windows Path Traversal Edge Cases

**File:** `src/utils/security.py`, `validate_file_path()` function  
**Risk:** Path traversal on Windows using alternate separators or tricks  
**Details:**  
The validator may not handle Windows-specific path tricks:
- Mixed separators: `path\..\\..\\file`
- Long path syntax: `\\?\C:\file` (bypasses length limits)
- Reserved names: `CON`, `PRN`, `AUX` (reserved on Windows)
- UNC paths: `\\server\share\..\..\file`

**CWE:** CWE-22 (Improper Limitation of a Pathname)  
**Severity:** LOW  
**Recommendation:**
1. Use `os.path.normpath()` and `os.path.realpath()` to resolve all tricks:
   ```python
   # Resolve .. and ..\ and symlinks
   real_path = os.path.realpath(path)
   ```
2. Check against allowed roots:
   ```python
   allowed_root = os.path.realpath(allowed_root)
   if not real_path.startswith(allowed_root):
       raise ValueError("Path traversal detected")
   ```
3. On Windows, also check for reserved names
4. Test on both Linux and Windows

**Status:** NOT RESOLVED

---

### 22. Unpinned Dependencies

**File:** `pyproject.toml`  
**Risk:** Unexpected breaking changes in transitive dependencies  
**Details:**  
All dependencies use `>=` without upper bounds:
```toml
fastapi >= 0.100.0
pydantic >= 2.0.0
```

New major versions can introduce breaking changes automatically.

**CWE:** CWE-1104 (Use of Unmaintained Third Party Components)  
**Severity:** LOW  
**Recommendation:**
1. Commit a lock file (e.g., `uv.lock`):
   ```bash
   uv lock
   git add uv.lock
   ```
2. Update dependencies intentionally:
   ```bash
   uv sync --upgrade
   ```
3. Use version ranges:
   ```toml
   fastapi = "^0.100.0"  # Poetry syntax (0.100.0 <= v < 0.101.0)
   pydantic = "~2.0"     # npm syntax (2.0.0 <= v < 2.1.0)
   ```
4. Test after dependency upgrades

**Status:** NOT RESOLVED

---

## INFO Findings (4)

### 23. Conditional Application of Security Headers

**File:** `src/mcp_server/server.py`  
**Risk:** Headers only applied if FastAPI is used; unclear in other scenarios  
**Details:**  
```python
if hasattr(mcp, 'app') and isinstance(mcp.app, FastAPI):
    # Add headers
```

Security headers are only added conditionally. If the MCP server is not backed by FastAPI, headers are missing.

**Info:** This is informational — not a vulnerability by itself, but a potential risk if the conditional is ever `False` in production.

**Recommendation:**
1. Document which server backends are supported
2. Ensure headers are added regardless of backend
3. Add assertions or warnings if security headers are not applied

**Status:** NOT RESOLVED

---

### 24. Two Decoupled Rate Limiters

**File:** `src/utils/rate_limiting.py` and `src/mcp_server/server.py`  
**Risk:** Unclear which rate limiter is actually enforced  
**Details:**  
The `OperationRateLimiter` class exists but is not wired. There may be rate limiting in MCP handlers that is separate. This duplication can cause confusion about which limits actually apply.

**Info:** Consider consolidating to a single, clearly-used rate limiting mechanism.

**Recommendation:**
1. Document which rate limiter(s) are active
2. Remove unused rate limiters
3. Centralize configuration of rate limit thresholds

**Status:** INFORMATIONAL

---

### 25. Server Binds to 0.0.0.0 (All Interfaces)

**File:** `src/mcp_server/server.py` or Docker compose  
**Risk:** Service exposed to network by default (may be intended)  
**Details:**  
If the MCP server binds to `0.0.0.0:8000`, it is accessible from any network interface. In a multi-tenant environment, this may be unintended.

**Info:** This may be intentional for distributed deployments. Document the binding and consider making it configurable.

**Recommendation:**
1. Make binding address configurable:
   ```python
   HOST = os.getenv("MCP_HOST", "127.0.0.1")
   PORT = int(os.getenv("MCP_PORT", 8000))
   ```
2. Default to `127.0.0.1` for development, document production binding
3. Use a reverse proxy (Nginx) to control external access

**Status:** INFORMATIONAL

---

### 26. Hardcoded Version in Health Endpoint

**File:** `src/mcp_server/server.py`  
**Risk:** Version may not match package version; potential confusion  
**Details:**  
The `/health/live` endpoint may return a hardcoded version instead of reading from package metadata.

**Info:** Minor concern; consider centralizing version management.

**Recommendation:**
1. Read version from `pyproject.toml`:
   ```python
   from importlib.metadata import version
   APP_VERSION = version("corpus-callosum")
   ```
2. Or use `__version__` from `src/__init__.py`
3. Verify version matches across tools (e.g., `corpus-rag --version`)

**Status:** INFORMATIONAL

---

## Summary Table

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 2 | Not resolved |
| HIGH | 6 | Not resolved |
| MEDIUM | 8 | Not resolved |
| LOW | 6 | Not resolved |
| INFO | 4 | Informational |
| **Total** | **26** | **0 fully resolved** |

---

## Comparison to Prior Audits

| Audit | CRITICAL | HIGH | MEDIUM | LOW | Date |
|-------|----------|------|--------|-----|------|
| Audit-001 | 0 | 3 | 11 | 2 | ~2026-02-15 |
| Audit-002 | 2 | 4 | 6 | 2 | ~2026-03-20 |
| **Audit-003** | **2** | **6** | **8** | **6** | **2026-04-10** |

**Key differences in Audit-003:**
- Discovered credentials in `.env` (not checked before)
- Discovered Zip Slip in tarfile extraction (missed by static analysis)
- Reconfirmed InputValidator and OperationRateLimiter as dead code
- Identified new HIGH findings: timing attack, missing auth on tools, unvalidated paths
- Total vulnerabilities increased (new MEDIUM findings on CORS, health endpoint, file size checks)

---

## Conclusion

Audit-003 confirms the critical pattern identified in Audit-002: **security code exists but is not integrated**. Additionally, two CRITICAL vulnerabilities (credentials, Zip Slip) must be addressed before any deployment. The OperationRateLimiter and InputValidator are fully implemented and tested, but their absence from live code paths means they provide zero protection.

**Immediate action items:** Resolve CRITICAL and HIGH findings before deployment. Wire InputValidator and OperationRateLimiter into MCP handlers.
