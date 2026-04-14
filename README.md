# CorpusCallosum

**Unified Learning and Knowledge Management Toolkit**

CorpusCallosum is a modular, AI-powered toolkit for personal knowledge management with RAG, flashcard generation, summaries, quizzes, video transcription, and orchestration workflows.

## Features

### Core Tools
- **RAG Agent**: Query your personal knowledge base with context-aware responses
- **Flashcard Generator**: Create study cards from your documents
- **Summary Generator**: Generate short, medium, or long summaries
- **Quiz Generator**: Build quizzes in Markdown, JSON, or CSV
- **Video Transcriber**: Convert lectures and videos into searchable text

### Platform Features
- **Unified CLI**: Main `corpus` command for daily use
- **Python CLI Interface**: Run the same tools with `python -m ...`
- **MCP Server Integration**: Expose tools to agent workflows
- **Multi-LLM Backend Support**: Ollama and compatible API backends
- **Unified Database**: Shared ChromaDB storage across tools
- **Developer Commands**: Cross-platform setup, test, lint, format, build, and clean

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/CorpusCallosum.git
cd CorpusCallosum

# Install the package so console scripts and python -m commands resolve cleanly
pip install -e .

# Optional: install developer tooling
pip install -e ".[dev]"
```

### Configuration

Start from the repo's example config:

```bash
cp configs/base.yaml my-config.yaml
```

Minimal config example:

```yaml
llm:
  backend: ollama
  endpoint: http://localhost:11434
  model: llama3
  temperature: 0.7

embedding:
  backend: ollama
  model: nomic-embed-text

database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store

paths:
  vault: ./vault
  scratch_dir: ./scratch
  output_dir: ./output
```

By default, Chroma uses local persistent storage at `./chroma_store`. In that mode, you do not need a separate ChromaDB Docker container. Use a Docker Chroma server only when you switch `database.mode` to `http`. A matching example is included at `configs/docker.yaml.example`.

If you use Ollama locally:

```bash
ollama serve
ollama pull llama3
```

## CLI Usage

### Option 1: Installed Console Scripts

After `pip install -e .`, the package exposes console scripts:

```bash
corpus --help
corpus db --help
corpus-secrets --help
corpus-api-keys --help
corpus-mcp-server --help
```

### Option 2: Python CLI Interface

The same functionality is available directly through Python modules:

```bash
python -m cli --help
python -m cli db --help
python -m utils.manage_secrets --help
python -m utils.manage_keys --help
python -m mcp_server.server --help
```

Use the installed `corpus` command when you want the shortest form. Use `python -m ...` when you want to stay inside an explicit Python environment or script tooling.

## Main Commands

### Unified CLI

The recommended top-level interface is:

```bash
corpus --help
python -m cli --help
```

#### RAG

```bash
corpus rag ingest ./documents --collection notes
python -m cli rag ingest ./documents --collection notes

corpus rag query "What is machine learning?" --collection notes
python -m cli rag query "What is machine learning?" --collection notes

corpus rag chat --collection notes
python -m cli rag chat --collection notes
```

#### Flashcards, Summaries, Quizzes

```bash
corpus flashcards --collection notes --count 15 --difficulty intermediate
python -m cli flashcards --collection notes --count 15 --difficulty intermediate

corpus summaries --collection notes --length medium
python -m cli summaries --collection notes --length medium

corpus quizzes --collection notes --count 10 --format markdown
python -m cli quizzes --collection notes --count 10 --format markdown
```

#### Video

```bash
corpus video transcribe ./lectures --course BIOL101 --lecture 1
python -m cli video transcribe ./lectures --course BIOL101 --lecture 1

corpus video clean transcript.md
python -m cli video clean transcript.md

corpus video augment transcript.md --auto
python -m cli video augment transcript.md --auto

corpus video pipeline ./lectures --course BIOL101 --lecture 1
python -m cli video pipeline ./lectures --course BIOL101 --lecture 1
```

#### Orchestrations

```bash
corpus orchestrate study-session --collection notes --topic "databases"
python -m cli orchestrate study-session --collection notes --topic "databases"

corpus orchestrate lecture-pipeline ./lecture.mp4 --course CS101 --lecture 3
python -m cli orchestrate lecture-pipeline ./lecture.mp4 --course CS101 --lecture 3

corpus orchestrate build-kb ./documents --collection kb
python -m cli orchestrate build-kb ./documents --collection kb

corpus orchestrate query-kb --collection kb "Explain neural networks"
python -m cli orchestrate query-kb --collection kb "Explain neural networks"
```

#### Developer Commands

```bash
corpus dev setup
python -m cli dev setup

corpus dev test --cov
python -m cli dev test --cov

corpus dev lint
python -m cli dev lint

corpus dev fmt
python -m cli dev fmt

corpus dev build
python -m cli dev build

corpus dev clean
python -m cli dev clean
```

## Direct Module Entry Points

If you do not want to go through the unified CLI, the direct module entry points still work:

```bash
python -m tools.rag.cli ingest ./documents --collection notes
python -m tools.rag.cli query "What is machine learning?" --collection notes
python -m tools.rag.cli chat --collection notes

python -m tools.flashcards.cli --collection notes --count 15
python -m tools.summaries.cli --collection notes --length medium
python -m tools.quizzes.cli --collection notes --count 10 --format json

python -m tools.video.cli transcribe ./lectures --course BIOL101 --lecture 1
python -m tools.video.cli pipeline ./lectures --course BIOL101 --lecture 1

python -m orchestrations.cli study-session --collection notes --topic "databases"
python -m orchestrations.cli build-kb ./documents --collection kb
```

## Legacy Console Scripts

The tool-specific `corpus-*` entry points remain available, but `corpus ...` is the preferred interface:

```bash
corpus-rag ingest ./documents --collection notes
corpus-rag query "What is machine learning?" --collection notes
corpus-rag chat --collection notes

corpus-flashcards --collection notes --count 15 --difficulty intermediate
corpus-summaries --collection notes --length medium
corpus-quizzes --collection notes --count 10 --format markdown

corpus-video transcribe ./lectures --course BIOL101 --lecture 1
corpus-video clean transcript.md
corpus-video augment transcript.md --auto
corpus-video pipeline ./lectures --course BIOL101 --lecture 1

corpus-orchestrate study-session --collection notes --topic "databases"
corpus-orchestrate lecture-pipeline ./lecture.mp4 --course CS101 --lecture 3
corpus-orchestrate build-kb ./documents --collection kb
corpus-orchestrate query-kb --collection kb "Explain neural networks"
```

## Database Management

```bash
corpus db list
python -m cli db list

corpus db backup notes --output ./backups/notes.tar.gz
python -m cli db backup notes --output ./backups/notes.tar.gz

corpus db restore ./backups/notes.tar.gz
corpus db backup-all --output-dir ./backups
corpus db export notes --output notes.json --format json
corpus db migrate old_collection new_collection
```

## Secrets and API Keys

```bash
# Secrets backed by the system keyring
corpus-secrets store OPENAI_API_KEY
python -m utils.manage_secrets store OPENAI_API_KEY

corpus-secrets get OPENAI_API_KEY
corpus-secrets list
corpus-secrets delete OPENAI_API_KEY
corpus-secrets migrate
corpus-secrets validate

# MCP server API keys
corpus-api-keys generate my-agent
python -m utils.manage_keys generate my-agent

corpus-api-keys list
corpus-api-keys revoke <key>
corpus-api-keys test <key>
```

## MCP Server

```bash
corpus-mcp-server
python -m mcp_server.server
```

Default CLI options:

```bash
corpus-mcp-server --host 127.0.0.1 --port 8000
python -m mcp_server.server --host 127.0.0.1 --port 8000
```

## CLI Reference

### Unified `corpus` Command

| Subcommand | Description |
|---|---|
| `corpus rag` | RAG agent: `ingest`, `query`, `chat` |
| `corpus flashcards` | Generate flashcards |
| `corpus summaries` | Generate summaries |
| `corpus quizzes` | Generate quizzes |
| `corpus video` | Video processing: `transcribe`, `clean`, `augment`, `pipeline` |
| `corpus orchestrate` | Workflows: `study-session`, `lecture-pipeline`, `build-kb`, `query-kb` |
| `corpus db` | Database utilities: `list`, `backup`, `restore`, `backup-all`, `export`, `migrate` |
| `corpus dev` | Developer utilities: `setup`, `test`, `lint`, `fmt`, `build`, `clean`, `completion` |

### Python Module Equivalents

| Command Family | Python Form |
|---|---|
| Unified CLI | `python -m cli` |
| RAG | `python -m tools.rag.cli` |
| Flashcards | `python -m tools.flashcards.cli` |
| Summaries | `python -m tools.summaries.cli` |
| Quizzes | `python -m tools.quizzes.cli` |
| Video | `python -m tools.video.cli` |
| Orchestrations | `python -m orchestrations.cli` |
| Database | `python -m db.management` |
| Secrets | `python -m utils.manage_secrets` |
| API Keys | `python -m utils.manage_keys` |
| MCP Server | `python -m mcp_server.server` |

## Configuration

Configuration is loaded from YAML and can be overridden by environment variables prefixed with `CC_`.

Load order:

1. Base config at `configs/base.yaml`
2. Tool config file, for example `my-config.yaml`
3. Environment overrides such as `CC_LLM_MODEL=mistral`

Example:

```yaml
llm:
  backend: ollama
  endpoint: http://localhost:11434
  model: llama3
  timeout_seconds: 120.0
  temperature: 0.7

embedding:
  backend: ollama
  model: nomic-embed-text

database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store

paths:
  vault: ./vault
  scratch_dir: ./scratch
  output_dir: ./output
```

For Docker or shared-server setups, copy `configs/docker.yaml.example` and switch the database section to `mode: http`.

## Project Structure

```text
CorpusCallosum/
├── src/
│   ├── cli.py                    # Unified CLI entry point
│   ├── cli_dev.py                # Developer command group
│   ├── config/                   # Configuration management
│   ├── db/                       # Database layer and management CLI
│   ├── llm/                      # LLM backend abstraction
│   ├── mcp_server/               # MCP server implementation
│   ├── orchestrations/           # Workflow orchestration CLI
│   ├── tools/                    # RAG, flashcards, summaries, quizzes, video
│   └── utils/                    # Shared utilities, secrets, auth, security
├── configs/
│   └── corpus_callosum.yaml      # Example configuration
├── docs/
├── tests/
└── pyproject.toml
```

## Development

Use either the installed script or the Python form:

```bash
corpus dev setup
corpus dev test --cov
corpus dev lint
corpus dev fmt
corpus dev build
corpus dev clean

python -m cli dev setup
python -m cli dev test --cov
python -m cli dev lint
python -m cli dev fmt
```

Underlying tools:

```bash
pip install -e ".[dev]"
pytest tests/
pytest --cov=src tests/
python -m ruff check src tests
python -m mypy src
python -m ruff format src tests
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Tool Usage](docs/tools-usage.md)
- [Configuration Guide](docs/configuration.md)
- [MCP Integration](docs/mcp-integration.md)
- [Docker Deployment](docs/docker-deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes with tests.
4. Run `corpus dev lint` and `corpus dev test`.
5. Open a pull request.

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE.
