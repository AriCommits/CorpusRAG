# T7: Update Entry Points, CLI, README, and Docs

**Sprint:** 3 (Parallel with T6)
**Time:** 1 hr
**Prerequisites:** T1-T5 merged (needs to know final API)
**Parallel-safe with:** T6 (different files — T6 touches server.py/tests, T7 touches pyproject/docs)

---

## Goal

Update `pyproject.toml` entry points, `README.md`, and `docs/mcp-integration.md` to reflect the new `--profile` and `--transport` flags. Add editor-specific configuration examples.

---

## Files to Modify

| File | Action |
|------|--------|
| `pyproject.toml` | MODIFY — entry points unchanged, but verify |
| `README.md` | MODIFY — update MCP section |
| `docs/mcp-integration.md` | MODIFY — add stdio/profile docs, editor configs |

---

## Changes

### `pyproject.toml`

The entry point stays the same — `corpus-mcp-server = "mcp_server.server:main"` — because `main()` still exists in the rewritten `server.py`. Verify this is correct. No other changes needed.

### `README.md` — Update Architecture and MCP Sections

Replace the current MCP-related content with:

```markdown
### MCP Server

CorpusRAG includes an MCP (Model Context Protocol) server for agentic editor integrations.

```bash
# Start for editor integration (stdio, dev tools only)
corpus-mcp-server --profile dev --transport stdio

# Start for HTTP access (all tools, with auth)
corpus-mcp-server --profile full --transport streamable-http --port 8000

# Disable auth for local development
corpus-mcp-server --profile full --transport streamable-http --no-auth
```

**Profiles:**
| Profile | Tools | Use Case |
|---------|-------|----------|
| `dev` | RAG ingest/query/retrieve, store_text, collections | Coding agents, editor integrations |
| `learn` | Flashcards, summaries, quizzes, video | Study workflows |
| `full` | Everything | Full access |

**Transports:**
| Transport | Flag | Use Case |
|-----------|------|----------|
| stdio | `--transport stdio` (default) | Editor integrations (Claude, Kiro, Neovim) |
| HTTP | `--transport streamable-http` | Remote access, cloud hosting |
```

Update the Architecture section to show the new `mcp_server/` structure:

```markdown
├── mcp_server/              # MCP server for agentic workflows
│   ├── server.py            #   Entry point and transport dispatch
│   ├── profiles.py          #   Profile-based tool registration
│   ├── middleware.py         #   HTTP auth, CORS, health (HTTP only)
│   └── tools/               #   Transport-agnostic tool implementations
│       ├── common.py         #     Shared config/db/validation
│       ├── dev.py            #     RAG + store_text tools
│       └── learn.py          #     Flashcard/summary/quiz/video tools
```

### `docs/mcp-integration.md` — Add Editor Configs

Add a new section with copy-paste configurations for popular editors:

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "dev", "--transport", "stdio"]
    }
  }
}
```

#### Kiro CLI (`.kiro/settings.json`)

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "dev", "--transport", "stdio"]
    }
  }
}
```

#### Neovim (codecompanion.nvim)

```lua
require("codecompanion").setup({
  adapters = {
    mcp = {
      name = "corpusrag",
      cmd = "corpus-mcp-server",
      args = { "--profile", "dev", "--transport", "stdio" },
    },
  },
})
```

#### OpenCode (`.opencode.json`)

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "dev", "--transport", "stdio"]
    }
  }
}
```

#### Custom config path

All editors support passing a custom config:

```bash
corpus-mcp-server --profile dev --transport stdio --config /path/to/my/config.yaml
```

---

## Session Prompt

```
I'm implementing Plan 9, Task T7 from docs/plans/plan_9/S3-T7-entrypoints.md.

Goal: Update pyproject.toml, README.md, and docs/mcp-integration.md for the new MCP server.

Please:
1. Read docs/plans/plan_9/S3-T7-entrypoints.md completely
2. Verify pyproject.toml entry point is correct (corpus-mcp-server = "mcp_server.server:main")
3. Update README.md:
   - Replace the MCP server section with the new --profile/--transport docs
   - Update the Architecture tree to show new mcp_server/ structure
   - Keep all other README content unchanged
4. Update docs/mcp-integration.md:
   - Add editor configuration examples (Claude, Kiro, Neovim, OpenCode)
   - Update the "Starting the MCP Server" section with new flags
   - Add profile and transport documentation
5. Do NOT modify any Python source files — this task is docs-only

Keep changes minimal and focused on MCP-related sections.
```

---

## Verification

```bash
# Entry point still works
python -c "from mcp_server.server import main; print('PASS: entry point importable')"

# README has new content
grep -q "profile" README.md && echo "PASS: README mentions profiles" || echo "FAIL"
grep -q "stdio" README.md && echo "PASS: README mentions stdio" || echo "FAIL"

# Docs have editor configs
grep -q "claude_desktop_config" docs/mcp-integration.md && echo "PASS" || echo "FAIL"
grep -q "codecompanion" docs/mcp-integration.md && echo "PASS" || echo "FAIL"
```

---

## Done When

- [ ] `pyproject.toml` entry point verified correct
- [ ] `README.md` MCP section updated with profiles/transports
- [ ] `README.md` Architecture tree updated
- [ ] `docs/mcp-integration.md` has editor config examples (Claude, Kiro, Neovim, OpenCode)
- [ ] No Python source files modified
