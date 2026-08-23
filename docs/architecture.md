# CorpusRAG Architecture Overview

CorpusRAG is a modular knowledge-management toolkit: ingest documents into
ChromaDB, retrieve them with a staged hybrid pipeline, and generate study
materials. Access is through a single `corpus` CLI and a **manually registered**
MCP subset — MCP is not an automatic projection of every CLI command.

## Design principles

1. **Kernel first** — `src/kernel.py` (`Corpus`) is ingest / ask / summarize /
   sample / complete. New utilities should call `sample` + `complete`, not add
   a new MCP/CLI tree by default.
2. **One collection namespace** — user-facing name `notes` is stored as `rag_notes`.
   Flashcards, summaries, and quizzes read that same collection.
3. **CLI is the full product** — MCP exposes a hand-picked subset. Default
   profile is `simple` (list, ingest, store_text, query, summarize).
4. **YAML configuration** — `configs/base.yaml` plus optional per-tool files,
   `CC_*` env overrides, then CLI flags.
5. **Pluggable LLM backends** — Ollama, OpenAI-compatible, Anthropic-compatible.

## System diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CorpusRAG                               │
├─────────────────────────────────────────────────────────────────┤
│  Access                                                         │
│  ┌──────────────────────┐     ┌──────────────────────────────┐  │
│  │  corpus CLI          │     │  corpus-mcp-server           │  │
│  │  ingest/ask/summarize│     │  profile simple (default)    │  │
│  │  + nested tools      │     │  (manual tool subset)        │  │
│  └──────────────────────┘     └──────────────────────────────┘  │
│  Python: from kernel import Corpus                              │
├─────────────────────────────────────────────────────────────────┤
│  Orchestration                                                  │
│  corpus orchestrate lecture-pipeline                            │
├─────────────────────────────────────────────────────────────────┤
│  Tools                                                          │
│  RAG · video · handwriting · summaries · flashcards · quizzes   │
├─────────────────────────────────────────────────────────────────┤
│  Backends                                                       │
│  LLM (Ollama / OpenAI-compat / Anthropic-compat)                │
│  ChromaDB  ·  parent JSON store per collection                  │
│  YAML config (base + tool files + CC_* env)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Modules (`src/`)

### Kernel (`kernel.py`)

`Corpus.from_config_path(...)` / `Corpus.from_loaded(config, db)`:

- `ingest_path` / `ingest_text`
- `ask` / `summarize`
- `sample` / `complete` — the extension point for new study utilities

CLI `corpus ingest|ask|summarize` and MCP `simple` call this object.

### Configuration (`config/`)

- `base.py` — `BaseConfig` (`llm`, `embedding`, `database`, `paths`) plus `raw`
  for unmodeled sections (`rag`, `flashcards`, `video`, …).
- `loader.py` — YAML load, deep merge, `CC_*` env overrides.

Tool configs (`RAGConfig`, `FlashcardConfig`, …) overlay a named YAML
section via `BaseConfig.split_section`.

Loading order: `configs/base.yaml` → optional tool YAML → `CC_*` env → CLI flags.

### Database (`db/`)

- `base.py` — `DatabaseBackend` ABC.
- `chroma.py` — persistent file store or HTTP client.
- `management.py` / `collections_cli.py` — `corpus db` and `corpus collections`.

Retrieval talks to `DatabaseBackend` directly (no LangChain vectorstore adapter).

**Collection names:** one prefix for RAG and study tools.

| Surface | Pattern | Example |
|---------|---------|---------|
| Ingest / query / flashcards / summaries / quizzes | `rag_<name>` | `rag_notes` |

Pass `--collection notes` everywhere. Parent documents are stored under
`parent_store/<collection>/` with `collection_name` metadata so BM25 stays
isolated per collection.

### LLM (`llm/`)

Strategy + factory: Ollama, OpenAI-compatible, Anthropic-compatible. Streaming
token iterators exist on backends; `RAGAgent.query` currently uses `complete()`.

### Tools (`tools/`)

| Package | Role |
|---------|------|
| `tools/rag/` | Ingest, sync, hybrid/semantic/keyword retrieval, TUI, agent |
| `tools/generation.py` | Shared collection sampling + LLM complete for study tools |
| `tools/flashcards/`, `summaries/`, `quizzes/` | Generators + export |
| `tools/video/` | Whisper transcription, visual OCR, jobs |
| `tools/handwriting/` | Vision OCR ingest via `RAGAgent.ingest_text` |
| `tools/ocr_client.py` | Shared Ollama vision HTTP helper |

Retrieval strategies (`hybrid`, `semantic`, `keyword`) are **names of one
staged pipeline** in `tools/rag/strategies/staged.py`: vector search, BM25,
RRF fusion, optional cross-encoder rerank. Stages are enabled/disabled per name.

### MCP (`mcp_server/`)

FastMCP server. Tools are registered by hand in `profiles.py` (`simple`,
`dev`, `learn`, `full`). Default profile is `simple`. Telemetry uses
`log_tool()`. Transports: stdio (default) and
`streamable-http`. Resource: `collections://list`. Prompt: `study_session_prompt`.

### Orchestrations (`orchestrations/`)

Only `LecturePipelineOrchestrator` remains: transcribe → optional clean →
RAG ingest → summary / flashcards / quiz. CLI:
`corpus orchestrate lecture-pipeline <video> --course <id> --lecture <n>`.

## Access patterns

### CLI (authoritative)

```
corpus
├── setup | doctor | ingest | ask | summarize | benchmark
├── tools
│   ├── rag (ingest, sync, query, chat, ui)
│   ├── video | handwriting | summaries
│   └── learning (flashcards, quizzes)
├── db | collections | dev
└── orchestrate lecture-pipeline
```

Full examples: [`src/CLI.md`](../src/CLI.md).

### MCP (manual subset)

See [`mcp-integration.md`](mcp-integration.md) for the CLI ↔ MCP table.
Handwriting, lecture-pipeline, TUI/sync/chat, and `corpus db` backup are
CLI-only.

## Data flow (RAG)

1. Ingest splits markdown into parent sections and child chunks.
2. Children + embeddings go to Chroma (`rag_<name>`).
3. Parents go to `parent_store/<name>/*.json`.
4. Query: staged retrieve → prompt with parent text → LLM complete.
