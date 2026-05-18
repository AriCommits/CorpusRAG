# CorpusRAG

**AI-powered knowledge base with RAG, MCP server, and study tools.**

Ingest your documents, query them with context-aware retrieval, and expose everything to AI agents via the Model Context Protocol. Optionally generate flashcards, summaries, and quizzes from your knowledge base.

## Quick Start

```bash
# 1. Install
pip install corpusrag

# 2. Run the setup wizard (configures LLM, database, vault path)
corpus setup

# 3. Start ChromaDB
cd .docker && docker compose up -d

# 4. Verify services are healthy
corpus doctor

# 5. Ingest your documents
corpus tools rag ingest ./my-docs --collection notes

# 6. Start using it
corpus tools rag ui                          # TUI chat (picks collection)
corpus tools rag ui -c notes                 # TUI with specific collection
corpus tools rag query "What is X?" -c notes # CLI query
corpus-mcp-server --profile dev              # MCP server for editors

# 7. Process video content
corpus tools video ingest lecture.mp4 -c notes
corpus tools video ingest-url "https://youtube.com/watch?v=..." -c notes
```

## What It Does

| Feature | Description |
|---------|-------------|
| **RAG Pipeline** | Hybrid search (vector + BM25 + reranking), parent-child chunking, incremental sync |
| **MCP Server** | Expose RAG tools to Claude, Kiro, Neovim, OpenCode, or any MCP-compatible editor |
| **store_text** | Let AI agents push plans, summaries, and context into your knowledge base |
| **TUI** | Rich terminal chat with slash commands, collection management, context controls |
| **Flashcards** | Generate study cards with Anki export |
| **Summaries** | Multi-length summaries with Markdown export |
| **Quizzes** | Multiple choice, true/false, short answer — export to JSON/CSV |
| **Video** | Transcribe lectures with Whisper, extract slide/chalkboard text with vision OCR, auto-ingest |
| **Handwriting** | OCR handwritten notes via vision models, chunk and ingest into RAG |

## CLI Overview

```
corpus
├── setup              # Interactive setup wizard
├── doctor             # Health checks (DB, LLM, embeddings)
├── benchmark          # Performance benchmarks
├── tools
│   ├── rag            # RAG pipeline (ingest, sync, query, chat, ui)
│   ├── video          # Video transcription + visual OCR
│   ├── handwriting    # Handwriting OCR ingest
│   ├── summaries      # Summary generation
│   └── learning
│       ├── flashcards # Flashcard generation + Anki export
│       └── quizzes    # Quiz generation
├── db                 # Database management (backup, export, restore)
├── collections        # Collection management (list, info, delete)
└── dev                # Development tools (test, lint, fmt)
```

Full CLI reference: [`src/CLI.md`](src/CLI.md)

## Installation

```bash
pip install corpusrag                    # Core (RAG + CLI + MCP)
pip install corpusrag[generators]        # + flashcards, summaries, quizzes
pip install corpusrag[video]             # + video transcription
pip install corpusrag[handwriting]       # + handwriting OCR
pip install corpusrag[full]              # Everything
pip install corpusrag[full,dev]          # Everything + dev tools
```

### CUDA / GPU Support

If using `uv` as your package manager, the PyTorch CUDA 12.8 index is already configured in `pyproject.toml`. Just run:

```bash
uv sync
```

If you need to reconfigure (e.g., different CUDA version), edit the `[tool.uv.sources]` and `[[tool.uv.index]]` sections in `pyproject.toml`. See the [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) for details.

## Configuration

```bash
corpus setup           # Interactive first-time setup
corpus setup --reset   # Reconfigure
```

For manual configuration:

```bash
cp configs/base.example.yaml configs/base.yaml
```

Key settings:

```yaml
llm:
  backend: ollama
  endpoint: http://localhost:11434
  model: gemma3:27b

embedding:
  backend: ollama
  model: nomic-embed-text

database:
  backend: chromadb
  mode: http
  host: localhost
  port: 8001
```

## Docker

```bash
# ChromaDB only
docker compose -f .docker/docker-compose.yml up -d

# With local Ollama
docker compose -f .docker/docker-compose.yml --profile ollama up -d

# Full stack
docker compose -f .docker/docker-compose.yml --profile full up -d
```

ChromaDB at `http://localhost:8001`, MCP server at `http://localhost:8000`.

## Project Structure

```
src/
├── cli.py                   # Unified CLI entry point
├── config/                  # Configuration loading and schemas
├── db/                      # Database abstraction (ChromaDB)
├── llm/                     # LLM backends (Ollama, OpenAI, Anthropic)
├── mcp_server/              # MCP server (Model Context Protocol)
├── tools/
│   ├── cli.py               # Tools group CLI
│   ├── rag/                 # RAG pipeline, TUI, strategies
│   ├── video/               # Video transcription + visual OCR
│   ├── handwriting/         # Handwriting OCR ingest
│   ├── summaries/           # Summary generation
│   └── learning/            # Learning tools (flashcards, quizzes)
├── orchestrations/          # High-level pipelines
└── utils/                   # Security, rate limiting, auth
```

## Documentation

- **CLI reference** → [`src/CLI.md`](src/CLI.md)
- **RAG tool** → [`src/tools/rag/README.md`](src/tools/rag/README.md)
- **Video tool** → [`src/tools/video/README.md`](src/tools/video/README.md)
- **Handwriting tool** → [`src/tools/handwriting/README.md`](src/tools/handwriting/README.md)
- **Summaries tool** → [`src/tools/summaries/README.md`](src/tools/summaries/README.md)
- **Learning tools** → [`src/tools/learning/README.md`](src/tools/learning/README.md)
- **MCP server** → [`src/mcp_server/README.md`](src/mcp_server/README.md)
- **Architecture** → [`docs/architecture.md`](docs/architecture.md)
- **Configuration** → [`docs/configuration.md`](docs/configuration.md)

## License

GNU General Public License v3.0
