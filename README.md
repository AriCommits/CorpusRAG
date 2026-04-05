# CorpusCallosum

Local-first RAG service for personal knowledge management.

## Quick Start

### Option 1: Interactive Setup (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the setup wizard
corpus-setup
# Or: python -m corpus_callosum setup
```

The setup wizard will guide you through:
- **Storage mode**: Local (no Docker) or Docker-based ChromaDB
- **LLM configuration**: Ollama endpoint and model selection
- **Embedding model**: Ollama (default) or sentence-transformers from HuggingFace

### Option 2: Manual Setup

```bash
# 1. Install
pip install -r requirements.txt

# 2. Copy and edit config
cp configs/corpus_callosum.yaml.example configs/corpus_callosum.yaml

# 3. Start Ollama (if not running)
ollama serve
ollama pull llama3
```

## Basic Usage (CLI)

```bash
# Ingest documents
corpus-ingest --path ./vault/my-notes --collection notes

# Ask a question
corpus-ask "What is photosynthesis?" --collection notes

# Generate flashcards
corpus-flashcards --collection notes

# List collections
corpus-collections

# Convert documents to markdown
corpus-convert ./documents

# Interactive setup
corpus-setup
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `corpus-ingest --path <path> --collection <name>` | Ingest documents |
| `corpus-ask "<question>" --collection <name>` | Ask a question |
| `corpus-flashcards --collection <name>` | Generate flashcards |
| `corpus-collections` | List all collections |
| `corpus-convert <path>` | Convert documents to markdown |
| `corpus-setup` | Interactive setup wizard |
| `corpus-api` | Start the REST API server |

### CLI Options

```bash
# corpus-ingest
corpus-ingest -p ./docs -c notes           # Basic usage
corpus-ingest -p ./docs -c notes --convert # Auto-convert unsupported files

# corpus-ask
corpus-ask "question" -c collection      # Short form
corpus-ask -q "question" -c collection   # Alternative
corpus-ask "question" -c col -m mistral  # Override model
corpus-ask "question" -c col -s session1 # Multi-turn conversation

# corpus-flashcards
corpus-flashcards -c collection              # Print to stdout
corpus-flashcards -c collection -o cards.txt # Save to file
corpus-flashcards -c collection -m llama3   # Override model

# corpus-collections
corpus-collections         # Plain list
corpus-collections --json  # JSON output

# corpus-convert
corpus-convert ./documents                          # Convert to corpus_converted/
corpus-convert ./docs --output-dir my_markdown      # Custom output directory
corpus-convert ./docs --dry-run                    # Preview without converting
```

## Python Module Interface

All CLI commands are also available via Python module for platform-agnostic usage:

```bash
# Ingest documents
python -m corpus_callosum ingest --path ./vault/my-notes --collection notes

# Ask a question
python -m corpus_callosum ask "What is photosynthesis?" --collection notes

# Generate flashcards
python -m corpus_callosum flashcards --collection notes

# List collections
python -m corpus_callosum collections

# Convert documents
python -m corpus_callosum convert ./documents --output-dir my_markdown

# Start setup wizard
python -m corpus_callosum setup

# Start API server
python -m corpus_callosum api
```

Run `python -m corpus_callosum` without arguments to see all available commands.

## Features

- Hybrid retrieval (semantic + BM25 + RRF fusion)
- Supports PDF, Markdown, TXT files
- Multi-turn conversations with session memory
- Flashcard generation and writing critique
- Rate limiting and API key authentication
- OpenTelemetry observability (optional)

## REST API

Start the server with `corpus-api`, then access `http://localhost:8080`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ingest` | POST | Ingest documents into a collection |
| `/query` | POST | Query with RAG (SSE stream) |
| `/critique` | POST | Get writing feedback (SSE stream) |
| `/flashcards` | POST | Generate study flashcards (SSE stream) |
| `/summarize` | POST | Summarize a collection |
| `/collections` | GET | List all collections |
| `/rate-limit` | GET | Check rate limit status |

API docs available at `/docs` (Swagger) and `/redoc`.

## Configuration

Config is loaded from `configs/corpus_callosum.yaml` or `CORPUS_CALLOSUM_CONFIG` env var.

### Storage Modes

CorpusCallosum supports two storage modes for ChromaDB:

| Mode | Use Case | Docker Required |
|------|----------|-----------------|
| `persistent` | Personal use, CLI | No |
| `http` | Production, multi-user | Yes |

**Local mode** (default): Data stored in `./chroma_store/` folder. No server needed.

```yaml
chroma:
  mode: persistent
```

**Docker mode**: Connects to ChromaDB running as a separate service.

```yaml
chroma:
  mode: http
  host: chroma  # Docker service name
  port: 8000
```

### Embedding Models

CorpusCallosum supports two embedding backends:

#### Ollama (Recommended - Default)
Uses the same Ollama service as your LLM. No separate downloads needed.

| Model | Dimensions | Quality | Notes |
|-------|------------|---------|-------|
| `nomic-embed-text` | 768 | Excellent | Optimized for longer context |
| `mxbai-embed-large` | 1024 | State-of-art | Higher quality, slightly slower |
| `all-minilm` | 384 | Good | Fast and efficient |

```yaml
embedding:
  model: nomic-embed-text
  backend: null  # Auto-detects Ollama from model name
```

#### sentence-transformers (HuggingFace)
Downloads models locally from HuggingFace Hub. Runs entirely offline after first download.

| Model | Dimensions | Size | Quality |
|-------|------------|------|---------|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | ~80MB | Good, fast |
| `sentence-transformers/all-mpnet-base-v2` | 768 | ~420MB | Better, slower |

```yaml
embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  backend: null  # Auto-detects sentence-transformers from model name
```

**Note**: The embedding model is locked per collection. Changing models requires deleting and re-ingesting the collection.

### Full Config Example

```yaml
paths:
  vault: ./vault
  chromadb_store: ./chroma_store

embedding:
  model: nomic-embed-text  # Or: sentence-transformers/all-MiniLM-L6-v2
  backend: null  # Auto-detects from model name

model:
  endpoint: http://localhost:11434  # Ollama endpoint (code appends /api/generate)
  name: llama3
  timeout_seconds: 120.0

chroma:
  mode: persistent  # or 'http' for Docker

server:
  host: 127.0.0.1
  port: 8080

chunking:
  size: 1000
  overlap: 100

retrieval:
  top_k_final: 10
```

## API Authentication

When `auth_enabled: true`, include your API key:

```bash
curl -H "X-API-Key: your-key" http://localhost:8080/health
```

## Docker

Docker is **optional** - only needed if you want to run ChromaDB as a service or deploy with observability.

```bash
# 1. Create Docker config
cp configs/corpus_callosum.docker.yaml.example configs/corpus_callosum.docker.yaml

# 2. Start services (from project root)
docker compose -f .docker/docker-compose.yml up --build
```

Includes:
- **ChromaDB**: Vector database service
- **OpenTelemetry Collector**: Metrics and traces
- **Jaeger**: Trace visualization at `http://localhost:16686`

> **Note**: When running inside Docker, use `chroma.mode: http` with `host: chroma`. When running CLI outside Docker, use `chroma.mode: persistent`.

## Project Structure

```
src/corpus_callosum/
  __main__.py     # Python module entry point
  cli.py          # CLI commands (ask, flashcards, collections)
  api.py          # FastAPI REST endpoints
  agent.py        # RAG orchestration
  retriever.py    # Hybrid search (semantic + BM25)
  ingest.py       # Document ingestion
  convert.py      # Document format conversion
  setup.py        # Interactive setup wizard
  config.py       # Configuration
  llm_backends.py # Multi-provider LLM support
  security.py     # Rate limiting, auth
  observability.py # OpenTelemetry tracing
  converters/     # Format converters (pdf, docx, html, rtf)
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
mypy src
```

## Troubleshooting

**Ollama not running**: Start with `ollama serve` and pull a model: `ollama pull llama3`

**Config not found**: Run `corpus-setup` or copy the example: `cp configs/corpus_callosum.yaml.example configs/corpus_callosum.yaml`

**ChromaDB connection error**: If using `mode: http`, ensure Docker is running. For local use, switch to `mode: persistent`.

**Embedding dimension mismatch**: Changing embedding models requires deleting the collection and re-ingesting. Delete `./chroma_store/` to start fresh.

**Observability errors**: Install optional deps: `pip install corpus-callosum[observability]`
