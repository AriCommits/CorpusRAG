# Plan 5: Rename, Setup Wizard, MCP Server & Security Remediation

## Overview

This plan covers four workstreams that should be executed in order:
1. **Rename** CorpusCallosum → CorpusRAG (unblocks everything)
2. **Security remediation** (fixes found during audit)
3. **TUI Setup Wizard** (highest-leverage user-facing feature)
4. **MCP Server hardening + tool surface** (production readiness)

---

## Phase 1 — Rename: CorpusCallosum → CorpusRAG

**Why first:** Every new file, import, CLI command, and doc page written after this will use the correct name. Doing it later means double work.

### 1.1 GitHub Repo

Already done — repo is `CorpusRAG`. GitHub auto-redirects the old URL.

### 1.2 Package Identity (`pyproject.toml`)

```toml
[project]
name = "corpusrag"

[project.scripts]
corpus       = "cli:main"
corpus-mcp   = "mcp_server.server:main"
corpus-setup = "setup_wizard:main"          # Phase 3
```

### 1.3 Source Code (200+ references across 40+ files)

**Python files with references (need import/string updates):**

| File | What to change |
|------|---------------|
| `src/__init__.py` | Module docstring |
| `src/cli.py` | Lines 1, 16, 18, 64 — banner, help text |
| `src/config/__init__.py` | Docstring |
| `src/config/base.py` | Docstring |
| `src/db/__init__.py` | Docstring |
| `src/db/management.py` | Lines 1, 55, 105, 721, 727 — strings, paths |
| `src/llm/__init__.py` | Lines 2, 4 |
| `src/mcp_server/__init__.py` | Lines 2, 5 |
| `src/mcp_server/server.py` | Lines 4, 29, 56, 67, 385, 391, 398, 511, 533, 559 — server name, descriptions |
| `src/orchestrations/__init__.py` | Lines 2, 4 |
| `src/orchestrations/cli.py` | Line 13 |
| `src/tools/flashcards/__init__.py` | Docstring |
| `src/tools/summaries/__init__.py` | Docstring |
| `src/utils/__init__.py` | Docstring |
| `src/utils/manage_keys.py` | Lines 2, 14, 126 — config path `~/.corpus_callosum/` |
| `src/utils/manage_secrets.py` | Lines 2, 128, 159, 702 — config path |
| `src/utils/secrets.py` | Line 31 — config dir name |
| `src/utils/auth.py` | Config path `~/.corpus_callosum/api_keys.json` |

**Config / infra files:**

| File | What to change |
|------|---------------|
| `.docker/Dockerfile` | Comment on line 1 |
| `.docker/docker-compose.yml` | Comment line 1, service name line 73 |
| `.docker/docker-compose.dev.yml` | Line 20 |
| `.docker/healthcheck.py` | Line 3 |
| `.docker/otel-collector-config.yaml` | Lines 1, 39 |
| `.github/workflows/ci.yml` | Lines 33, 59, 63, 65, 89, 102 |
| `scripts/lint_and_format.py` | Lines 2, 178, 201, 231 |
| `scripts/lint-and-format.sh` | Lines 2, 18 |

**Documentation (bulk find/replace, lower priority):**

- `README.md` (7 references)
- `docs/troubleshooting.md` (11 refs)
- `docs/architecture.md` (4 refs)
- `docs/configuration.md` (10 refs)
- `docs/docker-deployment.md` (5 refs)
- `docs/mcp-integration.md` (10 refs)
- `docs/tools-usage.md` (6 refs)
- `docs/phases/PHASE1-5_README.md` (many refs)
- `docs/plans/*.md` (scattered refs)

**Test files:**

| File | What to change |
|------|---------------|
| `tests/unit/test_mcp_server.py` | Line 30 |
| `tests/integration/test_llm_integration.py` | Lines 2, 102 |

### 1.4 Config Directory Migration

The user-local config dir changes from `~/.corpus_callosum/` to `~/.corpusrag/`. Add a one-time migration check:

```python
old = Path.home() / ".corpus_callosum"
new = Path.home() / ".corpusrag"
if old.exists() and not new.exists():
    old.rename(new)
    print("Migrated config directory to ~/.corpusrag/")
```

### 1.5 Execution Strategy

1. Global find/replace `corpus_callosum` → `corpus_rag` (Python identifiers)
2. Global find/replace `CorpusCallosum` → `CorpusRAG` (display names)
3. Global find/replace `corpus-callosum` → `corpusrag` (package/PyPI name)
4. Update `~/.corpus_callosum` → `~/.corpusrag` paths
5. Run tests, fix any remaining breakage
6. Single commit: `Rename CorpusCallosum → CorpusRAG across entire codebase`

---

## Phase 2 — Security Remediation

Findings from full audit of the codebase. Ordered by severity.

### 2.1 CRITICAL: MCP Server Validation Logic Error

**File:** `src/mcp_server/server.py` (lines 144-149, 184-189, 234-240, 283-298, 338-344)

**Bug:** `InputValidator.validate_query()` returns a string or raises `SecurityError`, but the MCP server checks `.is_valid` and `.message` attributes on the return value — which don't exist. This causes `AttributeError` at runtime, meaning **all input validation is bypassed**.

**Fix:** Either:
- (A) Make `validate_query()` etc. return a `ValidationResult(is_valid: bool, message: str)` dataclass, or
- (B) Change the MCP server to use try/except around the validator calls

Option (A) is cleaner and should be applied consistently across all 5 tool endpoints.

### 2.2 HIGH: Missing `top_k` Bounds Validation

**File:** `src/mcp_server/server.py` (lines 126, 193)

**Bug:** `top_k` parameter accepted from user input without bounds checking. A request with `top_k=1000000` causes resource exhaustion (DoS).

**Fix:** Add validation: `1 <= top_k <= 100` (configurable upper bound).

### 2.3 HIGH: Plaintext API Key Storage Without File Permissions

**File:** `src/utils/auth.py` (lines 56-73)

**Bug:** API keys written to `~/.corpus_callosum/api_keys.json` (soon `~/.corpusrag/`) in plaintext JSON. No `chmod 0o600` after write — on shared systems, other users can read the file.

**Fix:**
```python
import os, stat
os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
```

### 2.4 HIGH: Unvalidated Where Clause Inputs

**File:** `src/tools/rag/cli.py` (lines 62-87)

**Bug:** Tag and section filter values from CLI args go directly into ChromaDB where clauses without sanitization.

**Fix:** Validate that tag/section values are alphanumeric + limited punctuation before building where clauses. Reject values containing `$` or `{`.

### 2.5 MEDIUM: Symlink Following in File Ingest

**File:** `src/tools/rag/ingest.py` (lines 55-76)

**Bug:** `Path(path).expanduser().resolve()` follows symlinks. An attacker who controls the filesystem could create a symlink pointing to `/etc/passwd` or other sensitive files.

**Fix:** After resolving, check `Path.is_symlink()` on the original path. Optionally, verify the resolved path is within an allowed base directory.

### 2.6 MEDIUM: Overly Permissive CORS

**File:** `src/mcp_server/server.py` (lines 491-497)

**Bug:** `allow_origins=["https://localhost:*"]` matches any port.

**Fix:** Use explicit origins or load from config. For local-only use, `["http://localhost:8000", "http://localhost:3000"]` is sufficient.

### 2.7 MEDIUM: Silent Fallback in Secret Management

**File:** `src/utils/secrets.py` (lines 84-85, 109-110, 147-150)

**Bug:** When keyring or encryption fails, the code silently falls back to plaintext with only a warning. Users may not notice.

**Fix:** Add structured logging. In production mode, make encryption a hard requirement (fail instead of fallback).

### 2.8 LOW: In-Memory Rate Limiter

**File:** `src/utils/rate_limiting.py`

Not a vulnerability for single-instance local use. Document that distributed deployments need Redis-backed rate limiting.

---

## Phase 3 — TUI Setup Wizard

### 3.1 Architecture

New file: `src/setup_wizard.py` (top-level, registered as `corpus-setup` entry point).

Uses Textual's `Screen` + `ModalScreen` pattern. The wizard is a sequence of screens, each collecting one piece of configuration.

### 3.2 Wizard Flow

| Step | Screen | What it does | Key logic |
|------|--------|-------------|-----------|
| 1 | `WelcomeScreen` | Welcome message + Ollama detection | HTTP GET `localhost:11434/api/tags`. Green check or offer to pull models |
| 2 | `BackendScreen` | LLM + embedding backend selection | Dropdown: Ollama / OpenAI / Anthropic. Auto-fills model names per backend |
| 3 | `ChromaScreen` | ChromaDB mode selection | Persistent (local) vs HTTP (Docker). If Docker: offer to run `docker-compose up -d` |
| 4 | `VaultScreen` | Knowledge base path | File path input with default `./vault`. Creates directory on confirm |
| 5 | `TelemetryScreen` | Telemetry opt-in | Explicit yes/no with clear explanation of what's collected |
| 6 | `TestScreen` | Test ingest + demo query | Runs on bundled sample doc. Shows progress bar + first query result |

### 3.3 On Completion

- Writes `configs/corpus_rag.yaml` (merged with defaults from `configs/base.yaml`)
- Touches `.corpus_setup_complete` marker file
- Auto-launches `corpus rag ui --collection <chosen_collection>`

### 3.4 Auto-Trigger

In `src/tools/rag/tui.py` (the `ui` command entry point):

```python
if not Path(".corpus_setup_complete").exists():
    from setup_wizard import SetupWizardApp
    SetupWizardApp().run()
    return
```

### 3.5 Reset

```bash
corpus-setup --reset   # deletes .corpus_setup_complete, re-runs wizard
```

### 3.6 CLI Integration

```toml
[project.scripts]
corpus-setup = "setup_wizard:main"
```

Also add as subcommand: `corpus setup` in `src/cli.py`.

---

## Phase 4 — MCP Server Hardening + Tool Surface

### 4.1 Fix Existing MCP Server (from Phase 2 findings)

- Fix validation logic error (2.1)
- Add `top_k` bounds (2.2)
- Tighten CORS (2.6)

### 4.2 Finalize Tool Surface

The MCP server should expose these tools (maps 1:1 to existing agent/tool functions):

| MCP Tool | Maps to | Args |
|----------|---------|------|
| `query` | `agent.query()` | `question`, `collection`, `session_id?`, `top_k?` |
| `ingest` | ingest pipeline | `path`, `collection` |
| `generate_flashcards` | flashcard generator | `collection`, `count?` |
| `list_collections` | db management | — |
| `summarize` | summary generator | `collection` |
| `create_quiz` | quiz generator | `collection`, `count?` |

### 4.3 Transport

- **stdio** (primary): Works with Claude Desktop, Cursor, Zed, any spec-compliant MCP client
- **SSE** (secondary): Bolted onto existing FastAPI server for remote/Docker deployments

### 4.4 Install Story

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp",
      "args": []
    }
  }
}
```

---

## Milestone Schedule

| Week | Deliverable | Key files touched |
|------|------------|-------------------|
| 1 | **Phase 1: Rename** — global find/replace, test, commit | All 40+ files |
| 2 | **Phase 2: Security fixes** — critical + high items | `mcp_server/server.py`, `utils/auth.py`, `tools/rag/cli.py`, `utils/validation.py` |
| 3 | **Phase 3: Wizard skeleton** — screens, config write, auto-trigger | New `setup_wizard.py`, `cli.py`, `pyproject.toml` |
| 4 | **Phase 3: Wizard polish** — Ollama detection, docker-compose, demo ingest | `setup_wizard.py` |
| 5 | **Phase 4: MCP hardening** — validation fixes, tool surface, stdio transport | `mcp_server/server.py` |
| 6 | **README overhaul + PyPI publish** as `corpusrag` | `README.md`, `pyproject.toml` |

---

## Dependencies & Risks

| Risk | Mitigation |
|------|-----------|
| Rename breaks imports at runtime | Run full test suite after rename; use CI to catch regressions |
| Config migration loses user data | One-time migration copies `~/.corpus_callosum/` → `~/.corpusrag/`; never deletes old dir automatically |
| Wizard depends on Textual features | Already using Textual for TUI; wizard uses same framework |
| MCP validation fix changes API behavior | Existing behavior is broken (crashes); fix is strictly better |
| PyPI name `corpusrag` taken | Check availability before publish; fallback: `corpus-rag` |

---

## Appendix: Security Audit Summary

| # | Issue | Severity | File | Status |
|---|-------|----------|------|--------|
| 1 | MCP validation logic error (`.is_valid` on string) | CRITICAL | `mcp_server/server.py` | Phase 2 |
| 2 | Missing `top_k` bounds validation | HIGH | `mcp_server/server.py` | Phase 2 |
| 3 | Plaintext API keys without file permissions | HIGH | `utils/auth.py` | Phase 2 |
| 4 | Unvalidated ChromaDB where clause inputs | HIGH | `tools/rag/cli.py` | Phase 2 |
| 5 | Command injection risk (`eval` in shell completion) | HIGH | `cli_dev.py` | Phase 2 |
| 6 | Symlink following in file ingest | MEDIUM | `tools/rag/ingest.py` | Phase 2 |
| 7 | Overly permissive CORS | MEDIUM | `mcp_server/server.py` | Phase 4 |
| 8 | In-memory-only rate limiter | MEDIUM | `utils/rate_limiting.py` | Document |
| 9 | Silent fallback in secret management | MEDIUM | `utils/secrets.py` | Phase 2 |
| 10 | HTTP for dev config endpoints | LOW | `config/base.py` | Document |
| 11 | Missing crypto fallback | LOW | `utils/secrets.py` | Phase 2 |
| 12 | Docker runs as non-root | PASS | `.docker/Dockerfile` | N/A |
| 13 | `.gitignore` covers secrets | PASS | `.gitignore` | N/A |
