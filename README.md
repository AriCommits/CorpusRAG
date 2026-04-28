# CorpusRAG

**AI-powered knowledge base with RAG, MCP server, and study tools.**

Ingest your documents, query them with context-aware retrieval, and expose everything to AI agents via the Model Context Protocol. Optionally generate flashcards, summaries, and quizzes from your knowledge base.

## Quick Start

```bash
# 1. Install
pip install corpusrag

# 2. Run the setup wizard (configures LLM, database, vault path)
corpus setup

# 3. cd to .docker directory, and run docker compose up/ensure your containers are running
cd .docker; docker compose up;
# 4. Ingest your documents
corpus rag ingest ./my-docs --collection notes

# 5. Start using it
corpus rag ui --collection notes          # TUI chat interface
corpus rag query "What is X?" -c notes    # CLI query
corpus-mcp-server --profile dev           # MCP server for editors
```

The setup wizard walks you through LLM backend selection (Ollama/OpenAI/Anthropic), ChromaDB configuration, and knowledge base location. Run `corpus setup --reset` to reconfigure later.

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
| **Video** | Transcribe lectures with Whisper, clean with LLM, auto-ingest |

## Installation Extras

```bash
pip install corpusrag                    # Core (RAG + CLI + MCP)
pip install corpusrag[generators]        # + flashcards, summaries, quizzes
pip install corpusrag[video]             # + video transcription
pip install corpusrag[full]              # Everything
pip install corpusrag[full,dev]          # Everything + dev tools
```

## Configuration

The recommended way to configure CorpusRAG is the setup wizard:

```bash
corpus setup           # Interactive first-time setup
corpus setup --reset   # Reconfigure
```

For manual configuration, copy and edit the example:

```bash
cp configs/base.example.yaml configs/base.yaml
```

Key settings:

```yaml
llm:
  backend: ollama                          # ollama | openai_compatible | anthropic_compatible
  endpoint: http://localhost:11434
  model: gemma3:27b

embedding:
  backend: ollama
  model: nomic-embed-text

database:
  backend: chromadb
  mode: persistent                         # persistent | http
  persist_directory: ./chroma_store
```

## Docker

Run the MCP server with ChromaDB via Docker Compose:

```bash
# Minimal (ChromaDB + MCP server)
docker compose -f .docker/docker-compose.yml up

# With local Ollama
docker compose -f .docker/docker-compose.yml --profile ollama up

# Full stack (all services)
docker compose -f .docker/docker-compose.yml --profile full up
```

The MCP server is available at `http://localhost:8000` and ChromaDB at `http://localhost:8001`. See [`.docker/`](.docker/) for configuration details.

## Project Structure

```
src/
├── cli.py                   # Unified CLI entry point
├── config/                  # Configuration loading and schemas
├── db/                      # Database abstraction (ChromaDB)
├── llm/                     # LLM backends (Ollama, OpenAI, Anthropic)
├── mcp_server/              # MCP server (see src/mcp_server/README.md)
│   ├── server.py            #   Entry point and transport dispatch
│   ├── profiles.py          #   Profile-based tool registration
│   ├── middleware.py         #   HTTP auth, CORS, health (HTTP only)
│   └── tools/               #   Transport-agnostic tool implementations
├── tools/
│   ├── rag/                 # RAG pipeline, TUI, strategies
│   ├── flashcards/          # Flashcard generation + Anki export
│   ├── summaries/           # Summary generation
│   ├── quizzes/             # Quiz generation
│   └── video/               # Video transcription + cleaning
├── orchestrations/          # High-level pipelines
└── utils/                   # Security, rate limiting, auth
```

## Documentation

- **CLI usage** → [`src/CLI.md`](src/CLI.md)
- **MCP server** → [`src/mcp_server/README.md`](src/mcp_server/README.md)
- **Architecture** → [`docs/architecture.md`](docs/architecture.md)
- **Configuration** → [`docs/configuration.md`](docs/configuration.md)
- **Troubleshooting** → [`docs/troubleshooting.md`](docs/troubleshooting.md)

## License

GNU General Public License v3.0
