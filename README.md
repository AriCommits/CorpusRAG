# CorpusRAG

**Unified Learning and Knowledge Management Toolkit**

CorpusRAG is a modular, AI-powered toolkit for personal knowledge management with advanced RAG, flashcard generation, summaries, quizzes, video transcription, and orchestration workflows.

## ✨ Recent Improvements (Current Release)

### 🎯 Advanced RAG Architecture
- **Hybrid Search**: Combines semantic vector search with BM25 keyword matching for superior retrieval of technical terms and exact matches.
- **Reranking**: Uses a cross-encoder (`ms-marco-MiniLM-L-6-v2`) to re-score and refine retrieved documents, ensuring the most relevant context is sent to the LLM.
- **Incremental Syncing**: Hash-based document ingestion (SHA-256) ensures only new or modified files are processed, making updates instantaneous.
- **Parent-Child Retrieval**: Semantic markdown splitting creates parent documents stored in LocalFileStore with child chunks indexed for vector search.
- **Metadata Filtering**: Advanced filtering using `$contains` for list-valued tags and exact matching for section headers.
- **Context Preservation**: Tag lines and structural headers are preserved during parsing to provide the LLM with full metadata context.

### 🖥️ Terminal User Interface (TUI)
- **Rich Interactive UI**: Powered by **Textual**, featuring a dual-pane layout with a session sidebar and a scrollable, Markdown-rendered chat area.
- **Dynamic Filtering**: Apply **Tags** and **Sections** filters directly from the TUI sidebar to refine your retrieval context on the fly.
- **Persistent Sessions**: Conversation history is automatically saved and loaded from a local `.sessions/` directory, allowing you to resume any past chain of thought.
- **Async Execution**: Background workers keep the TUI responsive while the LLM generates responses or the RAG pipeline processes queries.

### 🔧 Developer Experience
- **Automated Code Quality**: `python scripts/lint_and_format.py --fix` auto-fixes Black, isort, and Ruff issues
- **Pre-push Checks**: Run `python scripts/lint_and_format.py --fix --test` before pushing to GitHub
- **Comprehensive Tests**: 120+ new unit and integration tests covering RAG, CLI, and generators
- **Developer Guide**: `LINT_AND_FORMAT.md` with IDE setup, GitHub Actions integration, and troubleshooting

### 🐳 Docker & Deployment
- **Local ChromaDB**: `docker-compose.yml` at project root for quick local setup
- **HTTP Mode Support**: Switch to `database.mode: http` for shared ChromaDB server
- **Containerized Workflows**: Full Docker integration for production deployments

### 🔨 Code Quality & Fixes
- **Fixed Generator Bugs**: FlashcardGenerator, QuizGenerator, SummaryGenerator now use real embedding-based retrieval
- **MCP Server Fixed**: Corrected attribute references for video and RAG configs
- **Config Alignment**: All defaults now match YAML configuration (gemma4:26b-a4b-it-q4_K_M, embeddinggemma)
- **Cross-Platform Paths**: Removed hardcoded `/tmp` paths, now uses `config.paths.scratch_dir`

### 📦 Simplified CLI
- **Removed Redundancy**: Standalone `corpus-rag`, `corpus-flashcards`, etc. removed — use `corpus rag`, `corpus flashcards` instead
- **Unified Interface**: Single `corpus` command with all subcommands
- **Direct Module Access**: `python -m tools.rag.cli` still works for direct access

## Features

### Core Tools
- **RAG Agent**: Query your personal knowledge base with context-aware responses and metadata filtering
- **Flashcard Generator**: Create study cards from documents with real semantic search
- **Summary Generator**: Generate short, medium, or long summaries using embedding-based retrieval
- **Quiz Generator**: Build quizzes in Markdown, JSON, or CSV formats
- **Video Transcriber**: Convert lectures and videos into searchable text with cleaning and augmentation

### Platform Features
- **Unified CLI**: Main `corpus` command for daily use
- **Python CLI Interface**: Run tools directly with `python -m ...`
- **MCP Server Integration**: Expose tools to agent workflows
- **Multi-LLM Backend Support**: Ollama, OpenAI, Anthropic, and compatible API backends
- **Unified Database**: Shared ChromaDB storage (persistent or Docker-based)
- **Advanced RAG**: Parent-child retrieval with semantic markdown splitting and metadata filtering
- **Developer Commands**: Setup, test, lint, format, build, and clean utilities

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/CorpusCallosum.git
cd CorpusCallosum

# Install the package for console scripts and python -m commands
pip install -e .

# Optional: install developer tooling (linting, testing, etc.)
pip install -e ".[dev]"
```

### Configuration

Start from the repo's example config:

```bash
cp configs/base.example.yaml my-config.yaml
```

Minimal config example:

```yaml
llm:
  backend: ollama
  endpoint: http://localhost:11434
  model: gemma4:26b-a4b-it-q4_K_M
  temperature: 0.7

embedding:
  backend: ollama
  model: embeddinggemma

database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store

rag:
  chunking:
    child_chunk_size: 800
    child_chunk_overlap: 100
  retrieval:
    top_k_semantic: 50
    top_k_bm25: 25
    top_k_final: 10
    rrf_k: 80
  parent_store:
    type: local_file
    path: ./parent_store

paths:
  vault: ./vault
  scratch_dir: ./scratch
  output_dir: ./output
```

**For Docker setup with ChromaDB server:**

```bash
# Start ChromaDB container
docker-compose up -d

# Update config
cp configs/base.example.yaml my-config.yaml
# Change: database.mode: http
```

If you use Ollama locally:

```bash
ollama serve
ollama pull gemma4:26b-a4b-it-q4_K_M
ollama pull embeddinggemma
```

## CLI Usage

### Unified Command (Recommended)

```bash
corpus --help
```

#### RAG with TUI and Metadata Filtering

```bash
# Launch the rich Terminal User Interface (Recommended for interactive study)
corpus rag ui --collection notes

# Ingest documents (incremental sync, semantic markdown splitting, tag extraction)
corpus rag ingest ./documents --collection notes

# Query with hybrid search (vector + BM25) and cross-encoder reranking
corpus rag query "What is machine learning?" --collection notes

# Query with list-valued tag filter
corpus rag query "machine learning" --collection notes --tag python --tag ml

# Query with section header filter
corpus rag query "algorithms" --collection notes --section "Sorting"

# Headless interactive chat
corpus rag chat --collection notes
```

#### Flashcards, Summaries, Quizzes

```bash
corpus flashcards --collection notes --count 15 --difficulty intermediate
corpus summaries --collection notes --length medium
corpus quizzes --collection notes --count 10 --format markdown
```

#### Video Processing

```bash
corpus video transcribe ./lectures --course BIOL101 --lecture 1
corpus video clean transcript.md
corpus video pipeline ./lectures --course BIOL101 --lecture 1
```

#### Orchestrations

```bash
corpus orchestrate study-session --collection notes --topic "databases"
corpus orchestrate lecture-pipeline ./lecture.mp4 --course CS101 --lecture 3
```

#### Database Management

```bash
corpus db list
corpus db backup notes --output ./backups/notes.tar.gz
corpus db restore ./backups/notes.tar.gz
```

#### Developer Commands

```bash
corpus dev setup
corpus dev test --cov
corpus dev lint
corpus dev fmt
corpus dev clean
```

### Code Quality & Testing

Before pushing to GitHub, ensure all checks pass:

```bash
# Check and auto-fix all linting/formatting issues
python scripts/lint_and_format.py --fix

# Run full checks including tests
python scripts/lint_and_format.py --fix --test

# Check only (no fixes)
python scripts/lint_and_format.py

# See LINT_AND_FORMAT.md for full documentation
```

The script runs:
- **Black** - Code formatting (88-char lines)
- **isort** - Import sorting
- **Ruff** - Fast linting (unused imports, syntax, etc.)
- **pytest** - Unit and integration tests (optional)

### Direct Module Entry Points

For direct access without the unified CLI:

```bash
# RAG
python -m tools.rag.cli ui --collection notes
python -m tools.rag.cli ingest ./documents --collection notes
python -m tools.rag.cli query "What is machine learning?" --collection notes
python -m tools.rag.cli query "ml" --collection notes --tag python --tag ml

# Flashcards
python -m tools.flashcards.cli --collection notes --count 15

# Video
python -m tools.video.cli transcribe ./lectures --course BIOL101 --lecture 1

# Orchestrations
python -m orchestrations.cli lecture-pipeline ./lecture.mp4 --course CS101 --lecture 3
```

## Configuration

Configuration is loaded in order with later values overriding earlier ones:

1. Base config at `configs/base.yaml`
2. Tool config file (e.g., `my-config.yaml`)
3. Environment overrides (e.g., `CC_LLM_MODEL=mistral`)

### RAG Configuration

```yaml
rag:
  # Child chunking for vector search
  chunking:
    child_chunk_size: 800        # Size of child chunks for vector store
    child_chunk_overlap: 100     # Overlap between chunks
  
  # Retrieval settings
  retrieval:
    top_k_semantic: 50           # Initial semantic search results to fetch
    top_k_bm25: 25               # Initial keyword search results to fetch
    top_k_final: 10              # Final number of results after RRF and reranking
    rrf_k: 80                    # Reciprocal Rank Fusion parameter
  
  # Parent document storage (for parent-child retrieval)
  parent_store:
    type: local_file             # local_file or in_memory
    path: ./parent_store         # Path to parent document store
  
  collection_prefix: rag         # Prefix for collection names
```

### Database Configuration

**Persistent mode (local, no Docker):**
```yaml
database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store
```

**HTTP mode (Docker ChromaDB):**
```yaml
database:
  backend: chromadb
  mode: http
  host: localhost
  port: 8000
```

## Project Structure

```text
CorpusCallosum/
├── src/
│   ├── cli.py                    # Unified CLI entry point
│   ├── config/                   # Configuration management
│   ├── db/                       # Database layer
│   ├── llm/                      # LLM backend abstraction (Ollama, OpenAI, Anthropic)
│   ├── mcp_server/               # MCP server implementation
│   ├── orchestrations/           # Workflow orchestration
│   ├── tools/
│   │   ├── rag/                  # RAG with parent-child retrieval
│   │   │   ├── ingest.py         # Document ingestion
│   │   │   ├── retriever.py      # Parent document retriever
│   │   │   ├── markdown_parser.py # Semantic markdown splitting
│   │   │   ├── storage.py        # LocalFileStore for parents
│   │   │   └── cli.py            # RAG CLI with tag/section filtering
│   │   ├── flashcards/
│   │   ├── summaries/
│   │   ├── quizzes/
│   │   └── video/
│   └── utils/                    # Shared utilities, secrets, auth
├── configs/
│   ├── base.yaml                 # Base configuration
│   ├── base.example.yaml         # Example with all options
│   └── docker.yaml.example       # Docker deployment example
├── docker-compose.yml            # Local ChromaDB Docker setup
├── scripts/
│   ├── lint_and_format.py        # Automated code quality checks
│   └── lint-and-format.sh        # Bash version
├── tests/
│   ├── unit/
│   │   ├── test_rag_components.py     # RAG internals
│   │   ├── test_rag_cli.py            # RAG CLI commands
│   │   ├── test_tool_generators.py    # Generator configs
│   │   └── ...                        # Other unit tests
│   ├── integration/
│   │   ├── test_rag_integration.py    # Parent-child RAG tests
│   │   └── ...                        # Other integration tests
│   └── security/                      # Security and validation tests
├── docs/
│   ├── LINT_AND_FORMAT.md        # Code quality guide (NEW)
│   ├── plans/plan_2.md           # Audit and upgrade plan
│   └── ...                       # Other documentation
└── pyproject.toml
```

## Development

### Code Quality Checks

**Before every commit/push:**
```bash
python scripts/lint_and_format.py --fix --test
```

**Without auto-fix:**
```bash
python scripts/lint_and_format.py
```

See [LINT_AND_FORMAT.md](LINT_AND_FORMAT.md) for detailed guide including:
- IDE setup (VS Code, PyCharm, vim)
- Pre-commit hooks
- GitHub Actions integration
- Common issues and fixes

### Running Tests

```bash
# All tests
pytest tests/

# With coverage report
pytest tests/ --cov=src

# RAG integration tests only
pytest tests/integration/test_rag_integration.py -v

# Specific test class
pytest tests/unit/test_rag_components.py::TestMarkdownParser -v
```

### Installing Development Tools

```bash
pip install -e ".[dev]"

# Or manually install linting tools
pip install black isort ruff pytest mypy
```

## RAG Pipeline Details

### Document Ingestion

1. **Semantic Markdown Splitting**: Documents split by headers (# ## ###) preserving semantic structure
2. **Tag Extraction**: Automatically extracts `#tags` from bulleted lists
3. **Parent Storage**: Full sections stored in LocalFileStore for context
4. **Child Chunking**: Parents recursively split into 400-char children with 50-char overlap
5. **Embedding**: Children embedded and stored in ChromaDB with parent linkage

### Retrieval (Parent-Child & Hybrid Architecture)

1. **Hybrid Search**: Query is processed simultaneously via semantic vector search (child chunks) and BM25 keyword matching (parent documents).
2. **Parent Lookup**: For vector results, the full parent document is retrieved from LocalFileStore using the `parent_id`.
3. **RRF Fusion**: Results from both search paths are combined using Reciprocal Rank Fusion (RRF) to prioritize documents that appear in both or rank highly in one.
4. **Cross-Encoder Reranking**: The top candidates are re-scored by a cross-encoder model to ensure the most contextually relevant documents are selected.
5. **Deduplication**: Multiple child chunks from the same parent result in only one high-quality parent document being returned.
6. **Context Synthesis**: The final, reranked parent documents are provided to the LLM for response generation.

### Metadata Filtering

Query results can be filtered by:
- **Tags**: `--tag python --tag ml` filters documents with those tags
- **Sections**: `--section "Sorting"` filters by section header

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks: `python scripts/lint_and_format.py --fix --test`
5. Verify all tests pass
6. Open a pull request

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE.

## Troubleshooting

See [LINT_AND_FORMAT.md](LINT_AND_FORMAT.md) for code quality issues and [docs/troubleshooting.md](docs/troubleshooting.md) for runtime issues.

### Common Issues

**GitHub Actions Failures**: Run `python scripts/lint_and_format.py --fix` before pushing

**ChromaDB Connection**: Ensure `docker-compose up -d` is running if using `database.mode: http`

**Import Errors**: Run `pip install -e .` after cloning

**Ollama Not Found**: Install from [ollama.ai](https://ollama.ai) and run `ollama serve`

## Changelog

### Latest Release
- ✅ **Hybrid Search**: Combined semantic vector search and BM25 for maximum precision.
- ✅ **Cross-Encoder Reranking**: Advanced relevance filtering before LLM synthesis.
- ✅ **Incremental Syncing**: SHA-256 hash-based ingestion for near-instant updates.
- ✅ **Interactive TUI**: New **Textual**-powered terminal interface for immersive study.
- ✅ **Persistent Chat**: Conversation history saved across sessions with context window management.
- ✅ **Improved Parsing**: Preserved metadata headers in document content for LLM context.
- ✅ Parent-child RAG retrieval with semantic markdown splitting.
- ✅ Metadata filtering by tags and sections.

See [docs/plans/plan_2.md](docs/plans/plan_2.md) for complete audit and upgrade details.
