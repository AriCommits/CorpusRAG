# Sprint 3 — Docs

**Plan:** docs/plans/plan_22/OVERVIEW.md
**Wave:** 3 of 3
**Can run in parallel with:** none — serial, last wave
**Must complete before:** nothing (closes the plan)

Requires Wave 2 **K2** and **K3**, and Wave 1 **F1**, merged.

---

## Agents in This Wave

### Agent A: D1 — Docs for kernel, simple MCP, flattened CLI, first-run

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `README.md` — Quick Start uses `corpus ingest` / `corpus ask`; MCP `--profile simple`
- `docs/architecture.md` — kernel as the Python extension point; MCP simple vs full
- `docs/mcp-integration.md` — default profile simple; tool list
- `docs/tools-usage.md` — top-level aliases; nested tree still valid
- `docs/troubleshooting.md` — persistent doctor; HTTP port 8001
- `docs/docker-deployment.md` — healthcheck v2 / host port 8001 (if the current text is wrong)
- `src/CLI.md` — ingest, ask, summarize
- `src/mcp_server/README.md` — simple profile
- `tests/test_cli_docs_consistency.py` — only if a new stale string belongs in `_STALE_PATTERNS`; documented `corpus …` examples must resolve

**Depends on:** K2, K3, F1
**Blocks:** none

**Instructions:**
Rewrite in place. Live Click tree is authoritative. Examples in fenced `bash` / `text` blocks that start with `corpus ` must resolve (`test_documented_command_examples_resolve`).

Must say, plainly:
1. Python extenders use `Corpus` (`ask`, `summarize`, `sample`, `complete`). New utilities are functions on `sample` + `complete`, not new MCP/CLI trees by default.
2. Recommended MCP: `corpus-mcp-server --profile simple` (now the default): ingest, store_text, query, summarize, list_collections.
3. Quick Start: install/setup as today, then `corpus ingest ./vault -c notes` and `corpus ask "…" -c notes`. Nested `corpus tools rag …` still works.
4. HTTP Chroma from the host is port **8001**. Persistent mode does not need Docker; `corpus doctor` works locally.
5. Wizard ingest is positional (`./vault`), not `--path`.

Do not invent extras, CUDA, or lecture-pipeline as the first-run path. Do not edit `docs/plans/`.

Keep `_STALE_PATTERNS` (CorpusCallosum, etc.). Add nothing that reintroduces `corpus rag ui` without `tools`.

**Definition of Done:**
- [ ] README Quick Start shows top-level ingest/ask and simple MCP.
- [ ] Architecture names `src/kernel.py` as the extension point.
- [ ] MCP docs list the five simple tools and the default profile.
- [ ] Troubleshooting: persistent doctor + port 8001.
- [ ] `pytest tests/test_cli_docs_consistency.py` passes.
- [ ] Tests written and passing for modified files.
- [ ] No regressions in existing tests.

---

## What this wave unblocks

Plan 22 is complete. Merge to the plan-21 branch (or main if 21 is already merged).
