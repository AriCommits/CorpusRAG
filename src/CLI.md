# CorpusRAG CLI Reference

All commands are available via the `corpus` entry point after `pip install corpusrag`.

```bash
corpus --help
```

## Command Tree

```
corpus
├── setup              # Interactive setup wizard
├── doctor             # Health checks (DB, LLM, embeddings)
├── ingest             # Ingest documents
├── ask                # Ask a collection
├── summarize          # Summarize a collection
├── benchmark          # Performance benchmarks
├── tools
│   ├── rag            # RAG pipeline
│   │   ├── ingest     # Ingest documents
│   │   ├── sync       # Incremental sync
│   │   ├── query      # One-shot query
│   │   ├── chat       # Interactive CLI chat
│   │   └── ui         # TUI chat interface
│   ├── video          # Video transcription + OCR
│   ├── handwriting    # Handwriting OCR ingest
│   ├── summaries      # Summary generation
│   └── learning
│       ├── flashcards # Flashcard generation
│       └── quizzes    # Quiz generation
├── db
│   ├── list           # List collections
│   ├── backup         # Backup collection(s)
│   ├── restore        # Restore from backup
│   ├── export         # Export collection data
│   └── migrate        # Migrate between collections
├── collections
│   ├── list           # List collections
│   ├── info           # Collection stats
│   ├── delete         # Delete collection
│   ├── update-path    # Update stored ingest path
│   └── manage         # TUI collection manager
├── dev                # Development tools
└── orchestrate
    └── lecture-pipeline  # Video → transcript → study materials
```

## Top-Level Commands

### Setup

```bash
corpus setup           # First-time interactive setup
corpus setup --reset   # Re-run wizard
```

### Doctor

```bash
corpus doctor                    # Check DB, LLM, embedding connectivity
corpus doctor --config alt.yaml  # Use alternate config
```

Persistent Chroma does not need Docker. HTTP mode talks to host port **8001**
(Compose publishes `8001:8000`).

### Ingest / ask / summarize

```bash
corpus ingest ./documents --collection notes
corpus ask "What is gradient descent?" -c notes
corpus summarize -c notes --length short
```

These call the same `Corpus` kernel as `corpus tools rag ingest` /
`corpus tools rag query`. Nested commands remain.

### Benchmark

```bash
corpus benchmark --collection notes --queries 10
```

## Tools

### RAG

```bash
# Ingest documents
corpus tools rag ingest ./documents --collection notes
corpus tools rag ingest ./lecture.pdf --collection cs101

# Query
corpus tools rag query "What is gradient descent?" --collection notes
corpus tools rag query "explain backprop" -c notes --strategy semantic

# Sync (incremental updates)
corpus tools rag sync --collection notes              # Uses stored ingest path
corpus tools rag sync ./documents --collection notes   # Explicit path
corpus tools rag sync ./docs -c notes --dry-run        # Preview changes

# TUI chat interface
corpus tools rag ui                    # Shows collection picker
corpus tools rag ui --collection notes # Direct to collection

# CLI chat
corpus tools rag chat --collection notes
```

Strategies: `hybrid` (default), `semantic`, `keyword`.

**TUI Keyboard Shortcuts:**

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open Collection Manager |
| `Ctrl+S` | Trigger Sync |
| `Ctrl+H` | Show Help |
| `Ctrl+Q` | Quit |

**TUI Slash Commands:**

| Command | Description |
|---------|-------------|
| `/help` | List all commands |
| `/collections` | Open collection manager |
| `/switch <name>` | Switch active collection |
| `/strategy <name>` | Switch retrieval strategy |
| `/filter <tag>` | Filter by tag |
| `/filter clear` | Clear filters |
| `/sync` | Run sync |
| `/sync status` | Preview changes |
| `/export <fmt>` | Export session |
| `/context` | Show context usage |
| `/clear` | Clear session |

### Video

Requires `pip install corpusrag[video]`.

```bash
corpus tools video ingest lecture.mp4 -c cs6301
corpus tools video ingest-url "https://youtube.com/watch?v=abc" -c ocw_mit
corpus tools video jobs
corpus tools video status <job_id>
```

### Handwriting

```bash
corpus tools handwriting ingest ./notes-photos -c handwritten
```

### Summaries

Requires `pip install corpusrag[generators]`.

```bash
corpus tools summaries generate --collection notes --length medium
corpus tools summaries generate -c notes --export markdown -o summary.md
```

### Learning

Requires `pip install corpusrag[generators]`.

```bash
# Flashcards
corpus tools learning flashcards generate --collection notes --count 15
corpus tools learning flashcards generate -c notes --export anki -o cards.apkg

# Quizzes
corpus tools learning quizzes generate --collection notes --count 10
corpus tools learning quizzes generate -c notes --format json -o quiz.json
```

## Database Management

```bash
corpus db list
corpus db backup my_collection -o backup.tar.gz
corpus db backup --all -o ./backups/
corpus db restore backup.tar.gz --name new_name --overwrite
corpus db export my_collection -o export.json              # Includes embeddings
corpus db export my_collection -o export.json --no-embeddings
corpus db migrate source_collection target_collection
```

## Collections

```bash
corpus collections list
corpus collections info my_collection
corpus collections delete my_collection
corpus collections update-path my_collection ./new/docs/path
corpus collections manage   # TUI manager
```

## Dev Tools

```bash
corpus dev test --cov
corpus dev lint
corpus dev fmt
```

## Orchestrate

High-level pipelines that chain multiple tools together. These workflows are
config-driven: you supply only the essential inputs on the command line, and all
other behavior (counts, summary length, cleaning, etc.) comes from configuration.

### Lecture Pipeline

Process a lecture video into a complete set of study materials (transcript,
summary, flashcards, and quizzes) in one command.

```bash
corpus orchestrate lecture-pipeline <video> --course <id> --lecture <n>

# Example
corpus orchestrate lecture-pipeline lecture01.mp4 --course BIOL101 --lecture 1
corpus orchestrate lecture-pipeline lecture01.mp4 -c BIOL101 -l 1 -o materials.md
```

Only the video path, `--course`, and `--lecture` are required. Everything else is
driven by configuration; supply a flag only when you want to override the
configured value for a single run.

## Configuration

All commands accept `--config <path>` (default: `configs/base.yaml`).

```bash
corpus tools rag query "hello" -c notes --config configs/production.yaml
```
