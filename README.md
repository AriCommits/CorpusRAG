# CorpusRAG

**AI-powered knowledge base with RAG, MCP server, and study tools.**

Ingest your documents, query them with context-aware retrieval, and expose everything to AI agents via the Model Context Protocol. Optionally generate flashcards, summaries, and quizzes from your knowledge base.

## Quick Start

```bash
# Install (minimal — RAG + CLI + MCP server)
pip install corpusrag

# Ingest your documents
corpus rag ingest ./my-docs --collection notes

# Query from the terminal
corpus rag query "What is gradient descent?" --collection notes

# Launch the TUI chat interface
corpus rag ui --collection notes

# Start the MCP server for your editor
corpus-mcp-server --profile dev --transport stdio
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

Copy and edit the example config:

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
