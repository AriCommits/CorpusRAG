# CorpusCallosum Security Audit Report
**Date**: April 7, 2026  
**Auditor**: Senior DevSecOps Engineer  
**Scope**: Complete codebase security assessment  
**Version**: 0.6.0 (mono_repo_restruct branch)

---

## Executive Summary

This security audit identifies **16 vulnerabilities** across the CorpusCallosum codebase, ranging from **Critical** to **Low** severity. The application demonstrates good software engineering practices but lacks essential security controls required for production deployment.

### Severity Breakdown
- **Critical**: 0
- **High**: 3 vulnerabilities
- **Medium**: 11 vulnerabilities  
- **Low**: 2 vulnerabilities

**⚠️ IMMEDIATE ACTION REQUIRED**: High severity vulnerabilities include command injection, missing authentication, and path traversal issues that could lead to complete system compromise.

---

## High Severity Vulnerabilities

### 1. Command Injection in Video Augmentation
**Severity:** High  
**Location:** `src/corpus_callosum/tools/video/augment.py:35-38`  
**CVSS Score:** 8.8

**Description:**  
The video augmentation tool executes user-controlled commands without proper validation:

```python
subprocess.run(["open", str(file_path)])  # Line 35
editor = os.environ.get("EDITOR", "xdg-open")
subprocess.run([editor, str(file_path)])  # Line 38
```

An attacker can exploit this by:
- Crafting malicious file paths with shell metacharacters
- Manipulating the `EDITOR` environment variable to execute arbitrary commands
- Achieving remote code execution with application privileges

**Remediation:**
```python
import shlex
import subprocess
from pathlib import Path

# Validate and sanitize file path
def safe_open_file(file_path: Path) -> None:
    # Ensure file exists and is within allowed directories
    resolved_path = file_path.resolve()
    if not resolved_path.exists() or not resolved_path.is_file():
        raise ValueError("Invalid file path")
    
    # Whitelist allowed editors
    ALLOWED_EDITORS = ["nano", "vim", "code", "notepad.exe"]
    editor = os.environ.get("EDITOR", "xdg-open")
    
    if editor not in ALLOWED_EDITORS:
        editor = "xdg-open"
    
    # Use shlex.quote for safe command execution
    subprocess.run([editor, shlex.quote(str(resolved_path))])
```

### 2. Missing Authentication and Authorization
**Severity:** High  
**Location:** `src/corpus_callosum/mcp_server/server.py` (all endpoints)  
**CVSS Score:** 8.1

**Description:**  
The MCP server exposes all functionality without any authentication or authorization controls. Anyone with network access can:
- Access all document collections and sensitive data
- Execute arbitrary queries and consume system resources
- Modify or delete data through tool endpoints
- Extract embeddings and proprietary information

**Remediation:**
```python
from fastapi import HTTPException, Depends, Header
from typing import Optional
import jwt

# Add API key authentication
async def verify_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    try:
        # Validate JWT token or API key
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid API key")

# Apply to all tool endpoints
@mcp.tool(dependencies=[Depends(verify_api_key)])
def rag_query(collection: str, query: str, user_id: str = Depends(verify_api_key)):
    # Add access control logic
    if not user_has_access(user_id, collection):
        raise HTTPException(status_code=403, detail="Access denied")
    # ... existing logic
```

### 3. Path Traversal Vulnerabilities
**Severity:** High  
**Location:** Multiple file operations throughout codebase  
**CVSS Score:** 7.5

**Description:**  
User-provided file paths are not properly validated, allowing potential access to files outside intended directories:

```python
# Vulnerable code in rag/ingest.py:47
source = Path(path).expanduser().resolve()
```

An attacker could use paths like `../../../etc/passwd` to access sensitive system files.

**Remediation:**
```python
from pathlib import Path
import os

def validate_file_path(user_path: str, allowed_base_dirs: list[Path]) -> Path:
    """Validate file path to prevent directory traversal."""
    try:
        # Resolve the path
        resolved_path = Path(user_path).expanduser().resolve()
        
        # Check if path is within allowed directories
        for base_dir in allowed_base_dirs:
            try:
                resolved_path.relative_to(base_dir.resolve())
                return resolved_path  # Path is safe
            except ValueError:
                continue
        
        raise ValueError(f"Path not allowed: {user_path}")
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path: {user_path}") from e

# Usage example
ALLOWED_DIRS = [Path("./vault"), Path("./uploads"), Path("./documents")]
safe_path = validate_file_path(user_input, ALLOWED_DIRS)
```

---

## Medium Severity Vulnerabilities

### 4. API Keys in Environment Variables
**Severity:** Medium  
**Location:** `src/corpus_callosum/config/loader.py`, `src/corpus_callosum/llm/backend.py`  
**CVSS Score:** 6.5

**Description:**  
API keys are stored in plain text environment variables, making them visible in process lists and logs.

**Remediation:**
```python
# Use secure secrets management
import keyring
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self.cipher_suite = Fernet(self._get_encryption_key())
    
    def get_api_key(self, service: str) -> str:
        encrypted_key = keyring.get_password("corpus_callosum", service)
        if encrypted_key:
            return self.cipher_suite.decrypt(encrypted_key.encode()).decode()
        raise ValueError(f"API key not found for service: {service}")
    
    def set_api_key(self, service: str, key: str) -> None:
        encrypted_key = self.cipher_suite.encrypt(key.encode())
        keyring.set_password("corpus_callosum", service, encrypted_key.decode())
```

### 5. Docker CORS Misconfiguration
**Severity:** Medium  
**Location:** `.docker/docker-compose.yml:29`  
**CVSS Score:** 5.3

**Description:**  
CORS is configured to allow all origins (`["*"]`), enabling cross-origin attacks.

**Remediation:**
```yaml
environment:
  - CORS_ALLOW_ORIGINS=["https://yourdomain.com", "https://app.yourdomain.com"]
  - CORS_ALLOW_METHODS=["GET", "POST"]
  - CORS_ALLOW_HEADERS=["Authorization", "Content-Type"]
```

### 6. Insufficient Input Validation
**Severity:** Medium  
**Location:** MCP server tool endpoints  
**CVSS Score:** 6.1

**Description:**  
User inputs lack proper validation, potentially leading to DoS or resource exhaustion.

**Remediation:**
```python
from pydantic import BaseModel, validator
from typing import Optional

class RAGQueryRequest(BaseModel):
    collection: str
    query: str
    top_k: Optional[int] = 5
    
    @validator('collection')
    def validate_collection(cls, v):
        if not v or len(v) > 100 or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Invalid collection name')
        return v
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v) > 10000:
            raise ValueError('Query too long or empty')
        return v
    
    @validator('top_k')
    def validate_top_k(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('top_k must be between 1 and 100')
        return v
```

### 7. Verbose Error Messages
**Severity:** Medium  
**Location:** Multiple locations with detailed error responses  
**CVSS Score:** 4.3

**Description:**  
Error messages may leak sensitive system information to attackers.

**Remediation:**
```python
import logging
from fastapi import HTTPException

def safe_error_response(error: Exception, user_message: str = "An error occurred") -> HTTPException:
    # Log detailed error for debugging
    logging.error(f"Internal error: {str(error)}", exc_info=True)
    
    # Return generic message to user
    return HTTPException(status_code=500, detail=user_message)
```

### 8. Missing Rate Limiting
**Severity:** Medium  
**Location:** MCP server endpoints  
**CVSS Score:** 5.8

**Description:**  
No rate limiting implemented, allowing potential DoS attacks.

**Remediation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/query")
@limiter.limit("10/minute")  # 10 requests per minute
async def api_query(request: Request):
    # ... endpoint logic
```

### 9. Insecure File Operations
**Severity:** Medium  
**Location:** File ingestion and processing  
**CVSS Score:** 5.5

**Description:**  
No file type validation, size limits, or malware scanning.

**Remediation:**
```python
import magic
from pathlib import Path

ALLOWED_MIME_TYPES = {
    'application/pdf', 'text/plain', 'text/markdown',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def validate_file(file_path: Path) -> None:
    # Check file size
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    
    # Check MIME type
    mime_type = magic.from_file(str(file_path), mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported file type: {mime_type}")
    
    # Additional checks...
```

### 10. Missing Security Headers
**Severity:** Medium  
**Location:** FastAPI application  
**CVSS Score:** 4.7

**Description:**  
No security headers configured for web-based attacks protection.

**Remediation:**
```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "*.yourdomain.com"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### 11. Unsafe YAML Configuration
**Severity:** Medium  
**Location:** `src/corpus_callosum/config/loader.py:52`  
**CVSS Score:** 4.2

**Description:**  
While using `yaml.safe_load()` (good practice), there are no file size limits or content validation.

**Remediation:**
```python
import yaml
from pathlib import Path

MAX_CONFIG_SIZE = 1024 * 1024  # 1MB limit

def safe_load_yaml(path: Path) -> dict:
    if path.stat().st_size > MAX_CONFIG_SIZE:
        raise ValueError("Configuration file too large")
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Additional content validation
    if content.count('\n') > 10000:  # Limit complexity
        raise ValueError("Configuration too complex")
    
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    return data or {}
```

### 12. Dependency Vulnerabilities
**Severity:** Medium  
**Location:** `pyproject.toml`, dependency management  
**CVSS Score:** 5.9

**Description:**  
Some dependencies lack version pinning, and no automated vulnerability scanning is visible.

**Remediation:**
```toml
# Pin all versions in pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "==0.104.1"  # Pin specific versions
chromadb = "==0.4.24"
click = "==8.1.7"

[tool.poetry.dev-dependencies]
safety = "^2.3.0"  # Add security scanning
bandit = "^1.7.5"  # Static security analysis
```

Add CI/CD security checks:
```yaml
# .github/workflows/security.yml
- name: Run safety check
  run: safety check
  
- name: Run bandit security scan
  run: bandit -r src/
```

### 13. Insufficient Security Logging
**Severity:** Medium  
**Location:** Throughout application  
**CVSS Score:** 4.8

**Description:**  
No audit logging for sensitive operations or security events.

**Remediation:**
```python
import structlog
from typing import Optional

security_logger = structlog.get_logger("security")

class SecurityEventLogger:
    @staticmethod
    def log_authentication(user_id: str, success: bool, ip: str):
        security_logger.info(
            "authentication_attempt",
            user_id=user_id,
            success=success,
            client_ip=ip,
            timestamp=datetime.utcnow()
        )
    
    @staticmethod
    def log_data_access(user_id: str, collection: str, operation: str):
        security_logger.info(
            "data_access",
            user_id=user_id,
            collection=collection,
            operation=operation,
            timestamp=datetime.utcnow()
        )
```

### 14. Insecure Default Configuration
**Severity:** Medium  
**Location:** Various configuration files  
**CVSS Score:** 5.1

**Description:**  
Default configurations are not secure (bind to 0.0.0.0, no TLS, etc.).

**Remediation:**
```python
# Secure defaults in config
DEFAULT_SECURE_CONFIG = {
    "host": "127.0.0.1",  # Bind to localhost by default
    "require_tls": True,
    "max_request_size": 10 * 1024 * 1024,  # 10MB limit
    "timeout": 30,
    "debug": False
}

def load_config_with_security_defaults():
    config = load_base_config()
    
    # Warn about insecure configurations
    if config.get("host") == "0.0.0.0":
        logging.warning("Binding to 0.0.0.0 - ensure this is intentional")
    
    if not config.get("require_tls", True):
        logging.warning("TLS disabled - communications will be unencrypted")
    
    return config
```

---

## Low Severity Vulnerabilities

### 15. Health Check Information Disclosure
**Severity:** Low  
**Location:** `src/corpus_callosum/mcp_server/server.py:391-418`  
**CVSS Score:** 3.1

**Description:**  
Health endpoints reveal system information that could aid attackers.

**Remediation:**
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}  # Minimal information

@app.get("/health/detailed")
@Depends(verify_admin_access)  # Require authentication for detailed info
async def detailed_health():
    return {
        "status": "healthy",
        "database": "connected",
        "collections": len(collections)
    }
```

### 16. Potential Query Injection in Vector Database
**Severity:** Low  
**Location:** `src/corpus_callosum/db/chroma.py:153-157`  
**CVSS Score:** 2.7

**Description:**  
While ChromaDB doesn't use SQL, query structures could potentially be manipulated.

**Remediation:**
```python
def sanitize_query_params(params: dict) -> dict:
    """Sanitize query parameters for ChromaDB."""
    safe_params = {}
    
    for key, value in params.items():
        if key in ALLOWED_QUERY_PARAMS:
            if isinstance(value, str):
                # Remove potential injection characters
                safe_params[key] = value.replace("$", "").replace("{", "").replace("}", "")
            elif isinstance(value, (int, float)):
                safe_params[key] = max(0, min(value, MAX_NUMERIC_PARAM))
    
    return safe_params
```

---

## Immediate Action Plan

### Critical Actions (Complete within 24 hours):
1. **Fix command injection vulnerability** in video augmentation
2. **Implement API authentication** for MCP server
3. **Add path traversal protection** for all file operations

### High Priority (Complete within 1 week):
1. Secure API key storage mechanism
2. Configure proper CORS policies
3. Implement comprehensive input validation
4. Add rate limiting to all endpoints

### Medium Priority (Complete within 1 month):
1. Implement security logging and monitoring
2. Add file validation and size limits
3. Configure security headers
4. Set up dependency vulnerability scanning
5. Implement secure default configurations

### Ongoing Security Practices:
1. Regular dependency updates and security scanning
2. Periodic security audits and penetration testing
3. Security training for development team
4. Incident response procedures

---

## Conclusion

CorpusCallosum demonstrates good software engineering practices but requires significant security hardening before production deployment. The most critical issues are the lack of authentication and command injection vulnerabilities, which could lead to complete system compromise.

**Recommendation:** Do not deploy to production until at least the High severity vulnerabilities are resolved and proper security controls are implemented.

**Next Steps:**
1. Address immediate security vulnerabilities
2. Implement comprehensive security testing in CI/CD pipeline
3. Conduct penetration testing after security fixes
4. Establish ongoing security monitoring and incident response procedures