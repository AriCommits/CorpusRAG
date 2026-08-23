# CorpusRAG MCP Integration Guide

CorpusRAG ships an MCP server (`corpus-mcp-server`) so editors and agents can
call a **hand-registered** subset of tools. CLI commands are **not**
auto-exposed. If a capability is missing from the table below, use the CLI.

## Start the server

```bash
corpus-mcp-server --profile simple
corpus-mcp-server --profile dev
corpus-mcp-server --profile learn
corpus-mcp-server --profile full
corpus-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000
```

Profiles:

| Profile | Tools |
|---------|--------|
| `simple` (default) | `list_collections`, `rag_ingest`, `store_text`, `rag_query`, `generate_summary` |
| `dev` | RAG ingest/query/retrieve, `store_text`, collections, telemetry |
| `learn` | flashcards/summary/quiz, transcribe/clean, video OCR jobs |
| `full` | `dev` + `learn` |

Default transport is stdio. HTTP uses FastMCP `streamable-http` (optional auth
middleware). Config comes from `configs/base.yaml` unless you pass `--config`.
Tool configs are built from `config.raw` so YAML `rag:` / `flashcards:` /
`video:` sections apply.

## Editor config

### Claude Desktop / similar

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "simple", "--transport", "stdio"]
    }
  }
}
```

## CLI ↔ MCP

| Capability | CLI | MCP |
|---|---|---|
| ingest / query / retrieve | `corpus ingest` / `corpus ask` / `corpus tools rag …` | `rag_ingest`, `rag_query`, `rag_retrieve` |
| store raw text | — | `store_text` |
| flashcards / summary / quiz | `corpus tools learning …` / `corpus tools summaries` | `generate_flashcards`, `generate_summary`, `generate_quiz` |
| video OCR jobs | `corpus tools video ingest` / `ingest-url` | `video_ingest_local`, `video_ingest_url`, `video_combined_pipeline`, `video_job_status`, `video_list_jobs` |
| transcribe / clean transcript | `corpus tools video …` | `transcribe_video`, `clean_transcript` |
| handwriting | `corpus tools handwriting ingest` | CLI-only |
| lecture pipeline | `corpus orchestrate lecture-pipeline` | CLI-only |
| TUI / sync / chat | `corpus tools rag ui` / `sync` / `chat` | CLI-only |
| db backup / restore / export | `corpus db` | CLI-only |
| collection list / info | `corpus collections` | `list_collections`, `collection_info` |
| telemetry | — | `get_estimate`, `query_telemetry` (dev/full) |

Collections use the same `rag_<name>` namespace as the CLI. Pass
`collection: "notes"` after ingesting with `--collection notes`.

## Resources and prompts

- Resource: `collections://list` — newline list of collection names.
- Prompt: `study_session_prompt(collection, topic)` — tells the agent to call
  `generate_summary`, then `generate_flashcards`, then `generate_quiz`.

There is no per-collection resource URI and no lecture-pipeline prompt.

## Tool notes

- `rag_ingest` only allows paths under the configured vault.
- `store_text` goes through `Corpus.ingest_text` (same collection as CLI ingest).
- `transcribe_video` uses Whisper on a local path; `collection` is returned in
  the JSON result but is not passed into Whisper.
- Video OCR ingest tools return a `job_id`; poll with `video_job_status`.
- Telemetry wrappers log duration via `log_tool()` when telemetry is enabled
  in config.

## Docker

```bash
cd .docker
docker compose up -d
```

MCP HTTP is published on host port 8000 (`corpus-mcp` service). See
[`docker-deployment.md`](docker-deployment.md).
