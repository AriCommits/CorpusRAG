# CorpusRAG CLI Reference

All commands are available via the `corpus` entry point after `pip install corpusrag`.

```bash
corpus --help
```

## RAG

### Ingest documents

```bash
corpus rag ingest ./documents --collection notes
corpus rag ingest ./lecture.pdf --collection cs101
```

### Query

```bash
corpus rag query "What is gradient descent?" --collection notes
corpus rag query "explain backpropagation" --collection notes --strategy semantic
```

Strategies: `hybrid` (default, best quality), `semantic` (faster), `keyword` (BM25 only).

### Sync (incremental updates)

```bash
# Preview what would change
corpus rag sync ./documents --collection notes --dry-run

# Apply changes
corpus rag sync ./documents --collection notes
```

Only new and modified files are processed. Deletions are detected automatically.

### TUI chat interface

```bash
corpus rag ui --collection notes
```

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `ctrl+l` | Open Collection Manager |
| `ctrl+s` | Trigger Incremental Sync |
| `ctrl+q` | Quit |

**Slash commands:**

| Command | Description |
|---------|-------------|
| `/help` | List all commands |
| `/strategy <name>` | Switch to `hybrid`, `semantic`, or `keyword` |
| `/filter <tag>` | Filter by tag (e.g., `/filter CS/ML`) |
| `/filter clear` | Clear filters |
| `/sync` | Run sync |
| `/sync status` | Preview changes |
| `/export <fmt>` | Export to `anki`, `markdown`, or `json` |
| `/context` | Show context usage |
| `/context clear` | Exclude old messages from context |
| `/clear` | Clear session |

## Collections

```bash
corpus collections list
corpus collections info my_collection
corpus collections rename old_name new_name
corpus collections merge source1 source2 destination
corpus collections delete my_collection
```

## Flashcards

Requires `pip install corpusrag[generators]`.

```bash
corpus flashcards generate --collection notes --count 15
corpus flashcards generate --collection notes --export anki --output cards.apkg
```

## Summaries

Requires `pip install corpusrag[generators]`.

```bash
corpus summaries generate --collection notes --length medium
corpus summaries generate --collection notes --export markdown --output summary.md
```

## Quizzes

Requires `pip install corpusrag[generators]`.

```bash
corpus quizzes generate --collection notes --count 10
corpus quizzes generate --collection notes --format json --output quiz.json
```

## Video Transcription

Requires `pip install corpusrag[video]`.

```bash
corpus video transcribe lecture.mp4 --collection cs101
corpus video clean transcript.txt --output cleaned.md
```

## Orchestrations

```bash
# Full lecture pipeline: transcribe → clean → ingest → generate materials
corpus orchestrate lecture lecture.mp4 --course CS101

# Study session: summary + flashcards + quiz from existing collection
corpus orchestrate study --collection notes --topic "neural networks"
```

## Benchmarking

```bash
corpus benchmark --collection notes --queries 10
```

## Setup Wizard

```bash
corpus setup           # First-time interactive setup
corpus setup --reset   # Re-run wizard
```

## Dev Tools

```bash
corpus dev test --cov
corpus dev lint
corpus dev fmt
```

## Configuration

All commands accept `--config <path>` to use a custom config file (default: `configs/base.yaml`).

```bash
corpus rag query "hello" --collection notes --config configs/production.yaml
```

## Environment Variables

Override any config value with `CC_` prefix:

```bash
CC_LLM_MODEL=mistral corpus rag query "hello" --collection notes
CC_DATABASE_MODE=http corpus rag ingest ./docs --collection notes
```
