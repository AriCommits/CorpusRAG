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
| `corpus-sync <subcommand>` | Synchronize collections between local and remote storage |
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
corpus-ask "question" -c col -k 5        # Retrieve top 5 results instead of default

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

# corpus-sync
corpus-sync status -c notes         # Check sync status
corpus-sync diff -c notes           # Show differences between local and remote
corpus-sync pull -c notes           # Pull from remote to local
corpus-sync push -c notes           # Push from local to remote
corpus-sync bidirectional -c notes  # Two-way sync
```

## Python Module Interface

All CLI commands are also available via Python module for platform-agnostic usage:

```bash
# Ingest documents
python -m corpus_callosum ingest --path ./vault/my-notes --collection notes

# Ask a question
python -m corpus_callosum ask "What is photosynthesis?" --collection notes

# Ask with dynamic retrieval count
python -m corpus_callosum ask "What is photosynthesis?" -c notes -k 5

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

# Sync collections (scaffolded - remote backends pending)
python -m corpus_callosum sync status -c notes
python -m corpus_callosum sync pull -c notes
```

Run `python -m corpus_callosum` without arguments to see all available commands.

## Features

- **Hybrid retrieval** (semantic + BM25 + RRF fusion)
- **Dynamic vector retrieval** - Adjust result count per query with `-k` parameter
- **Synchronization** - Sync collections between local and remote storage (scaffolded)
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

CorpusCallosum supports two embedding backends. Choose your backend explicitly in the config:

#### Ollama (Recommended - Default)
Uses the same Ollama service as your LLM. No separate downloads needed.

```yaml
embedding:
  model: nomic-embed-text  # Or: embeddinggemma, mxbai-embed-large, etc.
  backend: ollama
```

**Popular Ollama embedding models:**
- `nomic-embed-text` - 768 dimensions, excellent quality, optimized for longer context
- `mxbai-embed-large` - 1024 dimensions, state-of-the-art quality
- `all-minilm` - 384 dimensions, lightweight and fast

#### sentence-transformers (HuggingFace)
Downloads models locally from HuggingFace Hub. Runs entirely offline after first download.

```yaml
embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  backend: sentence-transformers
```

**Popular HuggingFace models:**
- `sentence-transformers/all-MiniLM-L6-v2` - 384 dimensions, ~80MB, good quality
- `sentence-transformers/all-mpnet-base-v2` - 768 dimensions, ~420MB, higher quality

**Note**: The embedding model is locked per collection. Changing models requires deleting and re-ingesting the collection.

### Full Config Example

```yaml
paths:
  vault: ./vault
  chromadb_store: ./chroma_store

embedding:
  model: nomic-embed-text  # Or: sentence-transformers/all-MiniLM-L6-v2
  backend: ollama  # Options: 'ollama' or 'sentence-transformers'

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

## Dynamic Vector Retrieval

Control the number of results retrieved per query using the `-k` / `--top-k` parameter:

```bash
# Retrieve only top 3 most relevant results
corpus-ask "What is machine learning?" -c ml-notes -k 3

# Default behavior (uses config's top_k_final value)
corpus-ask "What is machine learning?" -c ml-notes

# Python module interface
python -m corpus_callosum ask "question" -c collection -k 5
```

This parameter overrides the default `top_k_final` setting from your config on a per-query basis, allowing you to:
- Get more focused results with lower k values (e.g., `-k 3`)
- Retrieve comprehensive context with higher k values (e.g., `-k 20`)
- Optimize for specific use cases without changing your config

## Synchronization (Beta)

CorpusCallosum includes a synchronization framework for backing up and sharing collections between storage backends:

```bash
# Check sync status
corpus-sync status -c my-notes

# View differences between local and remote
corpus-sync diff -c my-notes

# Pull from remote to local
corpus-sync pull -c my-notes

# Push from local to remote
corpus-sync push -c my-notes

# Bidirectional sync
corpus-sync bidirectional -c my-notes
```

**Current Status**: The sync infrastructure is scaffolded with:
- Storage abstraction layer (`StorageBackend` interface)
- Local storage backend implementation
- Sync engine with diff/merge logic and conflict resolution strategies
- CLI commands for sync operations

**Pending**: Remote storage backend implementations (S3, HTTP API, etc.)


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
  cli.py          # CLI commands (ask, flashcards, collections, sync)
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
  storage/        # Storage abstraction layer
    base.py       # StorageBackend interface
    local.py      # LocalStorageBackend implementation
  sync/           # Synchronization engine
    engine.py     # SyncEngine with diff/merge logic
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
