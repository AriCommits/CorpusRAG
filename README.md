# CorpusRAG

**Unified Learning and Knowledge Management Toolkit**

CorpusRAG is a modular, AI-powered toolkit for personal knowledge management with advanced RAG, flashcard generation, summaries, quizzes, video transcription, and orchestration workflows.

## ✨ Recent Improvements (Current Release)

### 🖥️ Enhanced Terminal User Interface (TUI)
- **Slash Command Router**: Centralized command handling for `/help`, `/sync`, `/export`, `/clear`, and `/ask`.
- **Collection Manager**: Dedicated management screen (`ctrl+l`) to list, info, rename, merge, and delete ChromaDB collections.
- **Sync Dashboard**: Sidebar sync status with real-time feedback on new, modified, and deleted files. Trigger manual syncs with `ctrl+s`.
- **Latency Tracking**: Performance metrics displayed directly in assistant responses (e.g., `(450ms)`).

### 🎯 Advanced RAG & Data Management
- **Incremental Syncing**: Hash-based document ingestion (SHA-256) ensures only new or modified files are processed.
- **Export Subsystem**: Export study materials to external formats:
    - **Anki**: `.apkg` packages for flashcards (requires `genanki`).
    - **Markdown**: Formatted summaries with YAML frontmatter.
    - **JSON/CSV**: Structured data for quizzes.
- **Performance Benchmarking**: New `corpus benchmark` command to measure retrieval and generation latencies across query suites.
- **Traceable Metadata**: Ingestion now captures `source_file_name` for improved document attribution.

### 🔧 Developer Experience
- **Open MCP Standard**: High-performance MCP server implementation for agentic workflows.
- **Comprehensive Tests**: Expanded test suites for Slash Commands, Sync logic, and Benchmarking.
- **Robust Linting**: Zero-tolerance policy for linting errors using **Ruff**.

## Features

### Core Tools
- **RAG Agent**: Query your knowledge base with context-aware responses and metadata filtering.
- **Flashcard Generator**: Create study cards with real semantic search and **Anki export**.
- **Summary Generator**: Generate multi-length summaries with **Markdown export**.
- **Quiz Generator**: Build quizzes in Markdown, **JSON, or CSV** formats.
- **Video Transcriber**: Convert lectures into searchable text with cleaning and augmentation.

### Platform Features
- **Unified CLI**: Single `corpus` command for daily use.
- **Collection Management**: Full lifecycle management of vector stores via CLI or TUI.
- **Benchmarking**: Detailed latency tracking for retrieval and generation phases.
- **Advanced RAG**: Parent-child retrieval with hybrid search and cross-encoder reranking.

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/CorpusRAG.git
cd CorpusRAG

# Install the package
pip install -e .

# Optional: install export support (Anki) and dev tools
pip install -e ".[export,dev]"
```

## CLI Usage

### Unified Command (Recommended)

```bash
corpus --help
```

#### RAG & TUI

```bash
# Launch the rich TUI (with Slash Commands, Sync, and Collection Manager)
corpus rag ui --collection notes

# Sync directory with collection (detects changes automatically)
corpus rag sync ./documents --collection notes

# Run performance benchmarks
corpus benchmark --collection notes --queries 10
```

#### Collection Management

```bash
corpus collections list
corpus collections info my_collection
corpus collections rename old_name new_name
corpus collections merge source_col1 source_col2 destination_col
corpus collections manage  # Launches the TUI Collection Manager
```

#### Exporting Data

```bash
# Individual tool exports
corpus flashcards --collection notes --export anki --output cards.apkg
corpus summaries --collection notes --export markdown --output summary.md
corpus quizzes --collection notes --format json --output quiz.json

# Bulk export
corpus export --collection notes --output-dir ./my_exports
```

#### Developer Commands

```bash
corpus dev test --cov
corpus dev lint
corpus dev fmt
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
| `/sync status`| Check for file changes (dry-run) |
| `/export <fmt>`| Export to anki, markdown, or json |
| `/clear` | Clear current session history |
| `/ask <query>`| Explicit RAG query |

## Configuration

### RAG Configuration
```yaml
rag:
  chunking:
    child_chunk_size: 800
    child_chunk_overlap: 100
  retrieval:
    top_k_semantic: 50
    top_k_bm25: 25
    top_k_final: 10
  parent_store:
    type: local_file
    path: ./parent_store
```

## Changelog

### v0.5.0
- ✅ **Benchmarking**: Integrated latency tracking into RAG pipeline.
- ✅ **Collection Manager**: Added TUI and CLI tools for ChromaDB collection lifecycles.
- ✅ **Slash Commands**: Implemented extensible router for TUI interactions.
- ✅ **Export System**: Added support for Anki (.apkg), Markdown, and JSON/CSV.
- ✅ **Incremental Sync**: Hash-based change detection for optimized ingestion.
- ✅ **Quality**: Resolved all linting issues and fixed MCP server attribute bugs.

---
Licensed under the GNU GENERAL PUBLIC LICENSE.
