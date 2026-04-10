# Plan Implementation Status Review

**Date:** 2026-04-10
**Branch:** `mono_repo_restruct`
**Reviewer:** Claude Code (Opus 4.6)

---

## Overview

This document evaluates how well the three architecture/security plans in `.opencode/plans/arch/` and the two security audits in `.opencode/security/` were implemented in the current codebase.

| Plan | Target | Completion |
|------|--------|------------|
| plan_1.md | Mono-repo restructure (v0.5.0) | ~90% |
| plan_2.md | Security hardening + UX (v0.7.0) | ~50% |
| plan_3.md | Audit-002 remediation (v0.6.0) | ~35% |

---

## plan_1.md — Mono-Repo Restructure

**Goal:** Consolidate three separate repos (HomeSchool, RAG Pipeline, Video Transcription) into one unified toolkit.

### Phase Status

| Phase | Description | Status | Evidence |
|-------|-------------|--------|----------|
| 1 | Config system + DB abstraction | COMPLETE | `src/config/`, `src/db/chroma.py` exist with full implementation |
| 2 | Tool migration (RAG, flashcards, summaries, quizzes, video) | COMPLETE | All 5 tool directories under `src/tools/` with generators, configs, CLIs |
| 3 | MCP server + orchestrations | COMPLETE | `src/mcp_server/server.py`, `src/orchestrations/` with 3 orchestration modules |
| 4 | LLM integration (Ollama, OpenAI, Anthropic) | COMPLETE | `src/llm/backend.py` with `OllamaBackend`, `OpenAICompatibleBackend`, `AnthropicCompatibleBackend` |
| 5 | Docker/deployment + health checks | COMPLETE | `.docker/Dockerfile` (multi-stage), `docker-compose.yml`, `healthcheck.py` |
| 6 | Documentation + performance + final testing | IN PROGRESS | `docs/` directory populated; tests exist but coverage unknown |

### Design Decisions — Implemented vs Planned

| Decision | Planned | Actual |
|----------|---------|--------|
| Package layout | `src/corpus_callosum/` | Flattened to `src/` (plan_2 proposed this) |
| CLI framework | Click | Click + Typer + Rich (plan_2 proposed Typer migration) |
| MCP framework | FastMCP | FastMCP (as planned) |
| Config files | `configs/base.yaml` + per-tool | Single `corpus_callosum.yaml` + docker variant |
| Docker approach | Single container initially | Full compose with ChromaDB, Ollama, OTEL, Jaeger |
| Entry points | All 10 planned CLI commands | All 10 present in `pyproject.toml [project.scripts]` |

### Gaps

- **Success metrics not verified:** Plan specified >80% test coverage, <5s flashcard generation, <3s RAG query, <100ms MCP overhead. No benchmarks or coverage reports found.
- **Phase 6 incomplete:** Performance optimization and final testing not finished.

---

## plan_2.md — Security Hardening + UX (v0.7.0)

**Goal:** Address all 16 vulnerabilities from security-audit-001 + improve CLI, logging, and dependency management.

### Phase-by-Phase Status

#### Phase 1 — Critical Security Fixes: MOSTLY DONE

| Item | Status | Notes |
|------|--------|-------|
| Command injection fix (`augment.py`) | DONE | `src/utils/security.py` provides `safe_subprocess_run()`, `get_safe_editor()`, `validate_editor_command()` |
| Authentication (`AuthManager`) | DONE | `src/utils/auth.py` implements `MCPAuthenticator` with API key auth (not JWT as plan proposed) |
| Path traversal (`validate_file_path`) | DONE | `src/utils/security.py` implements path validation with `allowed_roots` |

#### Phase 2 — Secure Environment Management: MOSTLY DONE

| Item | Status | Notes |
|------|--------|-------|
| `SecureEnvironment` / keyring integration | DONE | `src/utils/secrets.py` implements `SecretManager` with Fernet encryption + keyring |
| `corpus setup` CLI command | DONE | `src/utils/manage_secrets.py` provides `corpus-secrets` CLI |
| Hardcoded values → config dataclasses | DONE | `src/config/base.py` has `BaseConfig`, `LLMConfig`, `DatabaseConfig`, etc. |

#### Phase 3 — Dependency Audit: NOT DONE

| Item | Status | Notes |
|------|--------|-------|
| `environment.yml` with conda-forge | NOT DONE | No `environment.yml` exists |
| Pinned dependencies | NOT DONE | All deps use `>=` in `pyproject.toml`; no lock file committed |
| Centralized imports module | NOT DONE | No `utils/imports.py` |

#### Phase 4 — Modern CLI: DONE

| Item | Status | Notes |
|------|--------|-------|
| Typer + Rich migration | DONE | `typer` and `rich` in dependencies; CLIs use Click/Typer |
| Single entry point with subcommands | PARTIAL | Individual `corpus-*` entry points exist; no unified `corpus` command |

#### Phase 5 — Structured Logging: PARTIAL

| Item | Status | Notes |
|------|--------|-------|
| `structlog` integration | PARTIAL | `structlog` is a dependency; used in some modules |
| `LoggingConfig` in base config | UNKNOWN | Not confirmed in `src/config/base.py` |
| Rotating file handler | UNKNOWN | Not confirmed |
| Separate security log | UNKNOWN | Not confirmed |

#### Phase 6 — Input Validation & Rate Limiting: CODE EXISTS, NOT WIRED

| Item | Status | Notes |
|------|--------|-------|
| `InputValidator` with Pydantic models | DONE (code) | `src/utils/validation.py` has `InputValidator` with pattern detection |
| Wired into MCP tools | **NOT DONE** | Only imported in `tests/security/test_prompt_injection.py` |
| `OperationRateLimiter` | DONE (code) | `src/utils/rate_limiting.py` has full implementation |
| Wired into MCP tools | **NOT DONE** | Never called from any handler |

#### Phase 7 — Security Headers: PARTIAL (with bugs)

| Item | Status | Notes |
|------|--------|-------|
| Security headers middleware | DONE | `src/mcp_server/server.py` adds X-Content-Type-Options, X-Frame-Options, HSTS, CSP |
| CORS middleware | BUGGY | Uses `"https://localhost:*"` which is not a valid starlette origin pattern |
| Conditional application | ISSUE | Headers only applied if `hasattr(mcp, 'app') and isinstance(mcp.app, FastAPI)` |

#### Phase 8 — Testing: PARTIAL

| Item | Status | Notes |
|------|--------|-------|
| `tests/security/test_vulnerabilities.py` | RENAMED | Exists as `test_yaml_security.py`, `test_prompt_injection.py`, `test_rate_limiting.py` |
| `tests/security/test_authentication.py` | NOT FOUND | No dedicated auth test file |
| `tests/performance/test_rate_limiting.py` | MOVED | In `tests/security/test_rate_limiting.py` instead |

---

## plan_3.md — Audit-002 Remediation (v0.6.0)

**Goal:** Remediate all 14 vulnerabilities from security-audit-002.

### Task Status

| # | Priority | Task | Status | Notes |
|---|----------|------|--------|-------|
| 1 | CRITICAL | YAML config key whitelist + content scanning | PARTIAL | `yaml.safe_load()` retained; no key whitelist, no dangerous pattern scanning, no file size check in loader |
| 2 | CRITICAL | Prompt injection protection | PARTIAL | `InputValidator` class created with patterns and length checks. **Not integrated into any live code path.** Dead code. |
| 3 | HIGH | Operation-specific rate limiting | PARTIAL | `OperationRateLimiter` class created with sliding window. **Not integrated into any MCP handler.** Dead code. |
| 4 | HIGH | Encrypted API key storage | PARTIAL | `SecretManager` in `src/utils/secrets.py` uses Fernet encryption for LLM API keys. However, `api_keys.json` (MCP auth keys) is still stored in plaintext. No key rotation. |
| 5 | HIGH | HTTPS/TLS enforcement | NOT DONE | No SSL context creation, no `--cert`/`--key` CLI args, no redirect middleware, no cert generation script |
| 6 | HIGH | ChromaDB auth + network isolation | NOT DONE | Docker compose still has CORS `["*"]` equivalent, no token auth, no internal network isolation |
| 7 | MEDIUM | PDF security validation | NOT DONE | No `SecurePDFProcessor`, no MIME validation, no JS scanning, no `python-magic` dependency |
| 8 | MEDIUM | Comprehensive security headers | PARTIAL | Headers added but CORS pattern is broken; missing several recommended headers |
| 9 | MEDIUM | Structured security logging | PARTIAL | `structlog` dependency exists; unclear how deeply integrated |
| 10 | MEDIUM | Secrets scanning CI/CD | NOT DONE | No `.github/workflows/security-scan.yml`, no Gitleaks, no TruffleHog, no pre-commit hooks |
| 11 | MEDIUM | Secure error handling | NOT DONE | `/health/ready` still returns raw `str(e)` to clients; LLM errors may expose internals |
| 12 | MEDIUM | Docker container hardening | NOT DONE | No `security_opt`, no `cap_drop`, no read-only root FS, no tmpfs, no Trivy |
| 13 | LOW | Dependency pinning | NOT DONE | All deps use `>=`; `.gitignore` explicitly excludes `uv.lock` |
| 14 | — | Multi-tenancy architecture | NOT DONE | Design phase only; no tenant scoping implemented |
| 15 | — | Backup & disaster recovery | PARTIAL | `corpus-db` CLI has backup/restore but no automated daily backups in compose |
| 16 | — | Compliance framework (GDPR) | NOT DONE | No data export, deletion, consent, or retention features |

---

## Security Audit Remediation Summary

### Audit-001 (16 findings)

| Severity | Total | Resolved | Partial | Open |
|----------|-------|----------|---------|------|
| HIGH | 3 | 2 | 1 | 0 |
| MEDIUM | 11 | 3 | 4 | 4 |
| LOW | 2 | 0 | 1 | 1 |

**Resolved:** Command injection, path traversal, auth implementation (basic)
**Partial:** API key storage (encrypted for LLM keys, not MCP keys), input validation (code exists, not wired), rate limiting (code exists, not wired), security headers (added with bugs)
**Open:** CORS wildcard, PDF validation, dependency pinning, secure defaults, security logging, Docker hardening

### Audit-002 (14 findings + 5 architectural)

| Severity | Total | Resolved | Partial | Open |
|----------|-------|----------|---------|------|
| CRITICAL | 2 | 0 | 2 | 0 |
| HIGH | 4 | 0 | 2 | 2 |
| MEDIUM | 6 | 0 | 2 | 4 |
| LOW | 2 | 0 | 1 | 1 |
| Architecture | 5 | 0 | 1 | 4 |

**Key pattern:** Code was written to address findings but never integrated into the live application paths. The `InputValidator` and `OperationRateLimiter` are the clearest examples — both are fully implemented with tests, but have zero imports outside of test files.

---

## Overall Assessment

The project has made strong progress on **architectural foundations** (plan_1) — the mono-repo consolidation is essentially complete with a clean modular structure. The **security implementation** (plans 2 and 3) shows a concerning pattern: security utilities were built and tested in isolation but not wired into the application. This creates a false sense of security — the code exists, the tests pass, but the protections are not active.

**Top priority:** Integrate existing security code (InputValidator, OperationRateLimiter, auth dependencies) into live MCP server handlers before any deployment.
