# CorpusRAG

**Unified Learning and Knowledge Management Toolkit**

CorpusRAG is a modular, AI-powered toolkit for personal knowledge management with advanced RAG, flashcard generation, summaries, quizzes, video transcription, and orchestration workflows.

## Recent Improvements

### Terminal User Interface (TUI)
- **Slash Command Router**: Centralized command handling for `/help`, `/sync`, `/export`, `/filter`, `/strategy`, `/clear`, `/ask`, and `/context`.
- **Collection Manager**: Dedicated management screen (`ctrl+l`) to list, info, rename, merge, and delete ChromaDB collections.
- **Sync Dashboard**: Sidebar sync status with real-time feedback on new, modified, and deleted files. Trigger manual syncs with `ctrl+s`.
- **Tag Filtering**: Hierarchical tag-based filtering via `/filter` slash command or sidebar input.
- **Strategy Switching**: Change retrieval strategy on the fly via `/strategy` slash command. Strategy visible in sidebar.
- **Selective Context Inclusion**: Toggle message inclusion in active context via switches on chat messages. Excluded messages are visually dimmed and not sent to LLM. Control via `/context` slash command or UI toggles. Context usage warning at 80% capacity.
- **Security Hardened**: Message ID validation (UUID format), session file integrity checks with SHA256 checksums, rate-limited context sync to prevent UI lag.

### Advanced RAG & Data Management
- **Pluggable Retrieval Strategies**: Switch between `hybrid`, `semantic`, and `keyword` strategies via config, CLI flag, or TUI.
- **Hierarchical Tag Taxonomy**: Tags support `#Subject/Subtopic` hierarchy (e.g., `#CS/ML`, `#Math/Linear_Algebra`) with prefix-based filtering.
- **VectorStore Agnosticism**: LangChain adapter layer allows swapping ChromaDB for Pinecone, Qdrant, Weaviate, FAISS, or any LangChain-supported backend.
- **Incremental Syncing**: Hash-based document ingestion (SHA-256) ensures only new or modified files are processed.
- **Export Subsystem**: Export study materials to Anki (`.apkg`), Markdown, JSON, and CSV.
- **Security Hardened**: Path traversal protection, symlink validation, metadata sanitization, and operator whitelisting.

### Developer Experience
- **Open MCP Standard**: High-performance MCP server implementation for agentic workflows.
- **Modular RAG Pipeline**: Parsing, embedding, retrieval, and storage separated into `pipeline/`, `strategies/`, and `vectorstores/` subpackages.
- **Token Estimation**: Utilities for estimating and formatting token counts for display and verification.
- **Context Management**: Structured context tracking with percentage calculations and inclusion/exclusion filtering.
- **Message Metadata**: Rich metadata tracking for chat messages including tags, timestamps, and context inclusion status.
- **Comprehensive Tests**: Expanded test suites for security, tag parsing, strategies, slash commands, sync logic, and context management.
- **Robust Linting**: Zero-tolerance policy for linting errors using **Ruff**.

## Features

### Core Tools
- **RAG Agent**: Query your knowledge base with context-aware responses and metadata filtering.
- **Flashcard Generator**: Create study cards with real semantic search and Anki export.
- **Summary Generator**: Generate multi-length summaries with Markdown export.
- **Quiz Generator**: Build quizzes in Markdown, JSON, or CSV formats.
- **Video Transcriber**: Convert lectures into searchable text with cleaning and augmentation.

### Platform Features
- **Unified CLI**: Single `corpus` command for daily use.
- **Collection Management**: Full lifecycle management of vector stores via CLI or TUI.
- **Pluggable Strategies**: Swap retrieval strategies at runtime without re-ingesting.
- **Advanced RAG**: Parent-child retrieval with hybrid search and cross-encoder reranking.
- **Orchestration Pipelines**: Lecture processing, study sessions, and knowledge base building.

## Quick Start

### Installation

CorpusRAG supports flexible installations for personal and public use cases:

```bash
# Minimal installation (RAG + TUI + MCP)
pip install corpusrag

# With generators (flashcards, summaries, quizzes)
pip install corpusrag[generators]

# With video transcription
pip install corpusrag[video]

# Full installation (all features)
pip install corpusrag[full]

# For development
pip install corpusrag[full,dev]
```

### Optional Extras

| Extra | Features | Dependencies |
|-------|----------|--------------|
| `generators` | Flashcards, summaries, quizzes | `tiktoken` |
| `video` | Video transcription & cleaning | `faster-whisper` |
| `export` | Export to Anki (`.apkg`) | `genanki` |
| `observability` | Telemetry & tracing (OpenTelemetry) | `opentelemetry-*` |
| `full` | Everything | All optional dependencies |
| `dev` | Development tools | `pytest`, `ruff`, `mypy` |

### First Run

```bash
# Ingest your documents
corpus rag ingest ./vault --collection notes

# Launch the TUI
corpus rag ui --collection notes
```

## CLI Usage

All commands are available via the installed `corpus` entry point or directly via Python:

```bash
corpus --help
# or, if the entry point isn't on your PATH:
python -m cli --help
```

### Available CLI Entry Points

- **`corpus`** (main): Primary entry point for all CorpusRAG commands
- **`corpus-mcp-server`**: MCP (Model Context Protocol) server for agentic integrations

> **Note:** If `corpus` fails with `ModuleNotFoundError`, reinstall the package:
> `pip install -e .`

### RAG & TUI

```bash
# Launch the rich TUI (with slash commands, sync, and collection manager)
corpus rag ui --collection notes
python -m cli rag ui --collection notes

# Ingest documents into a collection
corpus rag ingest ./documents --collection notes
python -m cli rag ingest ./documents --collection notes

# Sync directory with collection (detects changes automatically)
corpus rag sync ./documents --collection notes
python -m cli rag sync ./documents --collection notes

# Dry-run sync to preview changes
corpus rag sync ./documents --collection notes --dry-run

# Query with a specific retrieval strategy
corpus rag query "What is gradient descent?" --collection notes --strategy semantic
python -m cli rag query "What is gradient descent?" --collection notes --strategy semantic
```

### Collection Management

```bash
corpus collections list
corpus collections info my_collection
corpus collections rename old_name new_name
corpus collections merge source_col1 source_col2 destination_col
corpus collections delete my_collection
corpus collections manage   # Launches the TUI Collection Manager

# Python equivalents
python -m cli collections list
python -m cli collections info my_collection
```

### Exporting Data

```bash
# Individual tool exports (requires 'generators' extra)
corpus flashcards --collection notes --export anki --output cards.apkg
corpus summaries --collection notes --export markdown --output summary.md
corpus quizzes --collection notes --format json --output quiz.json

# Python equivalents
python -m cli flashcards --collection notes --export anki --output cards.apkg
```

> **Note:** Flashcards, summaries, and quizzes require the `generators` extra:
> ```bash
> pip install corpusrag[generators]
> ```

### Developer Commands

```bash
corpus dev test --cov
corpus dev lint
corpus dev fmt

# Python equivalents
python -m cli dev test --cov
python -m cli dev lint
```

## TUI Shortcuts & Slash Commands

| Key | Action |
|-----|--------|
| `ctrl+l` | Open Collection Manager |
| `ctrl+s` | Trigger Incremental Sync |
| `ctrl+q` | Quit Application |

| Slash Command | Description |
|---------------|-------------|
| `/help` | List all available commands |
| `/sync` | Run full synchronization |
| `/sync status` | Check for file changes (dry-run) |
| `/strategy` | Show current retrieval strategy |
| `/strategy <name>` | Switch to `hybrid`, `semantic`, or `keyword` |
| `/filter <tag>` | Filter results by tag prefix (e.g., `/filter CS`) |
| `/filter <tag/subtag>` | Filter by exact hierarchical tag (e.g., `/filter CS/ML`) |
| `/filter clear` | Clear all active filters |
| `/export <fmt>` | Export to `anki`, `markdown`, or `json` |
| `/clear` | Clear current session history |
| `/ask <query>` | Explicit RAG query |
| `/context` | Show context usage and management options |
| `/context show` | Toggle context sidebar visibility |
| `/context clear` | Exclude all messages except the last exchange |
| `/context include all` | Include all messages in the active context |

## Tag Taxonomy

CorpusRAG supports hierarchical tags in your Markdown documents. Tags are extracted from bulleted list items and stored as structured metadata for filtering.

### Tag Format

```markdown
- #Subject/Subtopic
- #CS/ML/Transformers
- #Math/Linear_Algebra
```

**Rules:**
- Top-level subjects: 1-2 words, PascalCase (e.g., `CS`, `Math`, `Skill`)
- Subtopics: can be longer, use `_` for spaces
- Maximum 3 levels deep: `#Subject/Area/Topic`
- Flat tags still work: `#Python` is equivalent to a single-level hierarchy

### Filtering by Tags

```bash
# In TUI slash commands
/filter CS              # All chunks tagged under CS/*
/filter CS/ML           # Only chunks tagged exactly CS/ML
/filter clear           # Remove all filters

# In CLI queries
corpus rag query "explain backpropagation" --collection notes --tags CS/ML
```

### Metadata Schema

Each chunk carries three tag-related metadata fields:

| Field | Example | Use Case |
|-------|---------|----------|
| `tags` | `["CS/ML", "Math/Linear_Algebra"]` | Exact tag match |
| `tag_prefixes` | `["CS", "Math"]` | Filter by subject area |
| `tag_leaves` | `["ML", "Linear_Algebra"]` | Filter by specific topic |

## Retrieval Strategies

CorpusRAG supports three retrieval strategies, configurable via `configs/base.yaml`, `--strategy` CLI flag, or `/strategy` TUI command.

| Strategy | Pipeline | Best For |
|----------|----------|----------|
| `hybrid` (default) | Vector + BM25 + RRF fusion + cross-encoder reranking | General-purpose queries, best quality |
| `semantic` | Vector similarity + optional reranking | Natural language questions, faster than hybrid |
| `keyword` | BM25 keyword matching only | Exact term matching, code search, no embedding model needed |

```yaml
# configs/base.yaml
rag:
  strategy: hybrid
  reranking:
    enabled: true
    model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

## Python API

CorpusRAG exposes a clean Python API for programmatic use. All components follow a consistent pattern: load config, initialize database, create tool.

### Quick Example

```python
from config import load_config
from db import ChromaDBBackend
from tools.rag import RAGAgent, RAGIngester

# Setup
config = load_config("configs/base.yaml")
db = ChromaDBBackend(config.database)

# Ingest documents
ingester = RAGIngester(config, db)
result = ingester.ingest_path("./vault", "notes")
print(f"Indexed {result.files_indexed} files, {result.chunks_indexed} chunks")

# Query
agent = RAGAgent(config, db)
response = agent.query("What is gradient descent?", "notes")
print(response)
```

### Configuration

```python
from config import load_config, BaseConfig

# Load from YAML
config = load_config("configs/base.yaml")

# Access nested config
print(config.llm.model)          # "gemma4:26b-a4b-it-q4_K_M"
print(config.embedding.backend)  # "ollama"
print(config.database.backend)   # "chromadb"
```

**Config classes:** `BaseConfig`, `LLMConfig`, `EmbeddingConfig`, `DatabaseConfig`, `PathsConfig`

### Database Layer

```python
from db import ChromaDBBackend, DatabaseBackend

db = ChromaDBBackend(config.database)

db.create_collection("my_collection")
db.list_collections()              # -> ["my_collection"]
db.collection_exists("my_collection")  # -> True
db.count_documents("my_collection")    # -> 42
db.get_collection_stats("my_collection")  # -> {doc_count, chunk_count, ...}
db.delete_collection("my_collection")
```

### RAG Tool

#### Ingestion

```python
from tools.rag import RAGIngester, IngestResult

ingester = RAGIngester(config, db)

# Ingest a single file or entire directory
result: IngestResult = ingester.ingest_path("./vault", "notes")
# result.collection, result.files_indexed, result.chunks_indexed
```

#### Sync (Incremental Updates)

```python
from tools.rag import RAGSyncer, SyncResult

syncer = RAGSyncer(config, db)

# Preview changes without applying
result: SyncResult = syncer.sync("./vault", "notes", dry_run=True)
print(f"New: {len(result.new_files)}, Modified: {len(result.modified_files)}, "
      f"Deleted: {len(result.deleted_files)}, Unchanged: {len(result.unchanged_files)}")

# Apply changes
result = syncer.sync("./vault", "notes")
```

#### Retrieval

```python
from tools.rag import RAGRetriever, RetrievedDocument

retriever = RAGRetriever(config, db)

# Retrieve with metadata filtering
docs: list[RetrievedDocument] = retriever.retrieve(
    query="explain transformers",
    collection="notes",
    top_k=10,
    where={"tag_prefixes": {"$contains": "CS"}},
)

for doc in docs:
    print(f"[{doc.score:.3f}] {doc.metadata.get('source_file')} — {doc.text[:100]}")
```

#### Agent (Retrieval + LLM Generation)

```python
from tools.rag import RAGAgent

agent = RAGAgent(config, db)

# Single query
response = agent.query("What is backpropagation?", "notes", top_k=5)

# Conversational chat with session persistence
response = agent.chat("Explain further", "notes", session_id="my_session")

# Query with metadata filter
response = agent.query(
    "Summarize linear algebra concepts",
    "notes",
    where={"tag_prefixes": {"$contains": "Math"}},
)
```

#### Strategy Switching

```python
from tools.rag import RAGRetriever

retriever = RAGRetriever(config, db)

# Check current strategy
print(retriever.strategy.name)  # "hybrid"

# Switch at runtime
retriever.set_strategy("semantic")   # Faster, vector-only
retriever.set_strategy("keyword")    # BM25-only, no embeddings
retriever.set_strategy("hybrid")     # Full pipeline
```

#### Custom Strategy

```python
from tools.rag.strategies import RAGStrategy, register_strategy

class MyStrategy:
    name = "custom"

    def __init__(self, vectorstore, embedder, parent_store, config):
        self.vectorstore = vectorstore
        # ...

    def retrieve(self, query, collection, top_k, where=None):
        # Your custom retrieval logic
        ...

    def initialize(self, collection):
        pass

register_strategy("custom", MyStrategy)
```

#### Alternative VectorStore (via LangChain)

```python
from langchain_qdrant import QdrantVectorStore
from tools.rag.vectorstores.langchain_adapter import LangChainVectorStoreAdapter

# Wrap any LangChain vectorstore
qdrant = QdrantVectorStore.from_existing(collection_name="notes", ...)
adapter = LangChainVectorStoreAdapter(qdrant)

# Use with any strategy
from tools.rag.strategies import get_strategy
strategy = get_strategy("hybrid", vectorstore=adapter, embedder=embedder, ...)
```

### Flashcards

```python
from tools.flashcards import FlashcardGenerator

gen = FlashcardGenerator(config, db)
cards = gen.generate("notes", difficulty="intermediate", count=15)
# cards: [{"front": "What is...?", "back": "It is..."}]
```

### Summaries

```python
from tools.summaries import SummaryGenerator

gen = SummaryGenerator(config, db)
result = gen.generate("notes", topic="machine learning")
# result: {"summary": "...", "keywords": [...], "outline": [...]}
```

### Quizzes

```python
from tools.quizzes import QuizGenerator

gen = QuizGenerator(config, db)
questions = gen.generate("notes", count=10, difficulty="intermediate")
# questions: [{"question": "...", "type": "multiple_choice", "options": [...], "correct_answer": "..."}]
```

### Video Transcription

```python
from tools.video import VideoTranscriber, TranscriptCleaner

transcriber = VideoTranscriber(config)
raw_text = transcriber.transcribe_file(Path("lecture.mp4"))

cleaner = TranscriptCleaner(config)
cleaned = cleaner.clean(raw_text)
```

### Orchestration Pipelines

```python
from orchestrations import StudySessionOrchestrator, LecturePipelineOrchestrator

# Generate a complete study session (summary + flashcards + quiz)
study = StudySessionOrchestrator(config, db)
session = study.create_session("notes", topic="neural networks")

# Process a lecture video end-to-end (transcribe -> clean -> ingest -> generate materials)
lecture = LecturePipelineOrchestrator(config, db)
result = lecture.process_lecture(Path("lecture.mp4"), course="CS101", lecture_num=5)
```

### LLM Backends

```python
from llm import create_backend, LLMBackend, LLMResponse

backend: LLMBackend = create_backend(config.llm)

# Completion
response: LLMResponse = backend.complete("Explain RAG in one sentence.")
print(response.text)

# Streaming
for chunk in backend.stream_completion("Explain RAG in detail."):
    print(chunk, end="")

# Chat
messages = [
    {"role": "user", "content": "What is RAG?"},
    {"role": "assistant", "content": "RAG stands for..."},
    {"role": "user", "content": "How does it work?"},
]
response = backend.chat(messages)
```

**Supported backends:** Ollama (`ollama`), OpenAI-compatible (`openai_compatible`), Anthropic-compatible (`anthropic_compatible`)

## Configuration

### Full RAG Configuration

```yaml
rag:
  strategy: hybrid              # hybrid | semantic | keyword
  chunking:
    child_chunk_size: 400
    child_chunk_overlap: 50
  retrieval:
    top_k_semantic: 50
    top_k_bm25: 50
    top_k_final: 25
    rrf_k: 80
  reranking:
    enabled: true
    model: cross-encoder/ms-marco-MiniLM-L-6-v2
  parent_store:
    type: local_file
    path: ./parent_store
  collection_prefix: rag
  vectorstore:
    backend: chromadb           # chromadb | langchain
    # langchain_class: langchain_qdrant.QdrantVectorStore
```

### LLM Configuration

```yaml
llm:
  backend: ollama
  endpoint: http://localhost:11434
  model: gemma4:26b-a4b-it-q4_K_M
  timeout_seconds: 120.0
  temperature: 0.7
  # Rate limiting (optional, for cloud API protection)
  rate_limit_rpm: null  # Requests per minute (null = unlimited, default for local)
  rate_limit_concurrent: null  # Max concurrent requests (null = unlimited)

embedding:
  backend: ollama
  model: embeddinggemma
```

**Rate Limiting:** CorpusRAG supports rate limiting for cloud API protection (OpenAI, Anthropic, etc.):
- Set to `null` (default) for unlimited requests (suitable for local Ollama)
- Set `rate_limit_rpm` to limit requests per minute (e.g., `60` for OpenAI tier 1)
- Set `rate_limit_concurrent` to limit simultaneous requests (e.g., `5`)
- When limits are exceeded, requests automatically wait before retrying

### Database Configuration

```yaml
database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store
```

## Architecture

```
src/
├── config/                  # Configuration loading and schemas
├── db/                      # Database abstraction (ChromaDB, etc.)
├── llm/                     # LLM backends (Ollama, OpenAI, Anthropic)
├── utils/                   # Security, rate limiting, auth
├── mcp_server/              # MCP server for agentic workflows
├── orchestrations/          # High-level pipelines (lecture, study session)
├── tools/
│   ├── rag/                 # RAG tool
│   │   ├── pipeline/        #   Parsing, embeddings, storage
│   │   ├── strategies/      #   Hybrid, semantic, keyword retrieval
│   │   ├── vectorstores/    #   ChromaDB + LangChain adapters
│   │   ├── agent.py         #   RAGAgent (query, chat, retrieve)
│   │   ├── ingest.py        #   Document ingestion
│   │   ├── sync.py          #   Incremental sync
│   │   ├── tui.py           #   Textual TUI
│   │   └── slash_commands.py#   Slash command router
│   ├── flashcards/          # Flashcard generation + Anki export
│   ├── summaries/           # Summary generation + Markdown export
│   ├── quizzes/             # Quiz generation + JSON/CSV export
│   └── video/               # Video transcription + cleaning
└── cli.py                   # Unified CLI entry point
```

## Changelog

### v0.7.0 (Upcoming)
- **Rate Limiting**: LLM backend now supports configurable rate limiting (RPM and concurrent request limits) for cloud API protection.
- **Token Estimation**: Utilities for estimating token counts with formatter for display (e.g., "1.5k").
- **Context Management**: `ContextBlock` and `ContextSidebar` for structured context tracking and token usage calculation.
- **Message Metadata**: Dataclass for rich message metadata with tags, timestamps, and context inclusion status.
- **Test Coverage**: 55+ new tests for token estimation, context management, and message metadata.

### v0.6.0
- **Hierarchical Tags**: Migrated from flat `#Tag` to `#Subject/Subtopic` taxonomy with prefix-based filtering.
- **Pluggable Strategies**: RAG retrieval now supports `hybrid`, `semantic`, and `keyword` strategies, switchable at runtime.
- **RAG Modularization**: Pipeline split into `pipeline/`, `strategies/`, and `vectorstores/` subpackages.
- **VectorStore Agnosticism**: LangChain adapter enables any LangChain-supported vector database.
- **Security Hardening**: Path traversal protection in LocalFileStore, symlink validation, metadata sanitization.
- **New Slash Commands**: `/filter`, `/strategy` for in-TUI control.
- **Python API Documentation**: Full programmatic API documented with examples.

### v0.5.0
- Benchmarking: Integrated latency tracking into RAG pipeline.
- Collection Manager: Added TUI and CLI tools for ChromaDB collection lifecycles.
- Slash Commands: Implemented extensible router for TUI interactions.
- Export System: Added support for Anki (.apkg), Markdown, and JSON/CSV.
- Incremental Sync: Hash-based change detection for optimized ingestion.
- Quality: Resolved all linting issues and fixed MCP server attribute bugs.

---
Licensed under the GNU GENERAL PUBLIC LICENSE.
