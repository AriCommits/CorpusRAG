# CorpusRAG MCP Server

Expose your RAG knowledge base to AI agents via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Quick Start

```bash
# For editor integration (Claude, Kiro, Neovim, OpenCode)
corpus-mcp-server --profile dev --transport stdio

# For HTTP access (remote/cloud)
corpus-mcp-server --profile full --transport streamable-http --port 8000
```

## Profiles

Profiles control which tools are available. Use `--profile` to select one.

### `dev` — for coding agents

| Tool | Description |
|------|-------------|
| `rag_ingest` | Ingest documents from a file or directory |
| `rag_query` | Query the knowledge base and get an LLM-generated answer |
| `rag_retrieve` | Retrieve relevant chunks without LLM generation |
| `store_text` | Store arbitrary text (plans, summaries, snippets) for later retrieval |
| `list_collections` | List all collections |
| `collection_info` | Get stats for a collection |

### `learn` — for study workflows

| Tool | Description |
|------|-------------|
| `generate_flashcards` | Generate flashcards from a collection |
| `generate_summary` | Generate a summary from a collection |
| `generate_quiz` | Generate a quiz from a collection |
| `transcribe_video` | Transcribe video with Whisper |
| `clean_transcript` | Clean a transcript with LLM |

### `full` — everything

All tools from both `dev` and `learn`.

## Transports

| Transport | Flag | Use Case |
|-----------|------|----------|
| **stdio** (default) | `--transport stdio` | Editor integrations — agent communicates via stdin/stdout |
| **HTTP** | `--transport streamable-http` | Remote access, cloud hosting, Docker deployments |

HTTP transport adds CORS, security headers, API key auth, and health endpoints (`/health`, `/health/ready`). Disable auth for local dev with `--no-auth`.

## Editor Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

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

### Kiro

Add to `.kiro/settings.json` or your workspace MCP config:

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

### Neovim (codecompanion.nvim)

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

### OpenCode

Add to `.opencode.json`:

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

### Custom config path

```bash
corpus-mcp-server --profile dev --transport stdio --config /path/to/config.yaml
```

## The `store_text` Tool

This is the key tool for agentic workflows. It lets an agent push text directly into the RAG knowledge base without needing a file on disk.

**Use cases:**
- Store implementation plans so future sessions can retrieve them instead of re-reading
- Save session summaries for continuity across conversations
- Push code snippets with descriptions for semantic search later

**Example call from an agent:**

```json
{
  "tool": "store_text",
  "arguments": {
    "text": "## Plan: Refactor auth module\n\n1. Extract FastAPI deps...",
    "collection": "plans",
    "metadata": {"type": "plan", "project": "corpusrag"}
  }
}
```

Then later, retrieve it:

```json
{
  "tool": "rag_retrieve",
  "arguments": {
    "collection": "plans",
    "query": "auth module refactor",
    "top_k": 3
  }
}
```

## All CLI Flags

```
corpus-mcp-server [OPTIONS]

Options:
  --config, -c PATH          Config file (default: configs/base.yaml)
  --profile {dev,learn,full} Tool profile (default: full)
  --transport {stdio,streamable-http}
                             Transport type (default: stdio)
  --host TEXT                Bind host, HTTP only (default: 0.0.0.0)
  --port INT                 Bind port, HTTP only (default: 8000)
  --no-auth                  Disable API key auth, HTTP only
```

## Architecture

```
src/mcp_server/
├── server.py        # 82-line entry point — arg parsing, wiring, mcp.run()
├── profiles.py      # register_dev_tools(), register_learn_tools(), register_profile()
├── middleware.py     # apply_http_middleware() — CORS, auth, health (HTTP only)
└── tools/
    ├── common.py    # init_config(), init_db(), validation helpers
    ├── dev.py       # rag_ingest, rag_query, rag_retrieve, store_text, collections
    └── learn.py     # flashcards, summaries, quizzes, video
```

Tool logic in `tools/` is transport-agnostic — pure functions that take `config` and `db` as arguments. `profiles.py` wraps them with `@mcp.tool()` decorators. `middleware.py` is only loaded for HTTP transport.
