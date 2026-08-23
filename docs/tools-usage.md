# CorpusRAG Tool Usage Guide

All commands go through the `corpus` entry point (`pip install corpusrag`).
This page is a practical tour. The live tree and flags live in
[`src/CLI.md`](../src/CLI.md).

```bash
corpus --help
```

## Command tree

```
corpus
├── setup              # Interactive setup wizard
├── doctor             # Health checks (DB, LLM, embeddings)
├── benchmark          # Performance benchmarks
├── tools
│   ├── rag            # ingest, sync, query, chat, ui
│   ├── video          # ingest, ingest-url, jobs, status
│   ├── handwriting    # ingest
│   ├── summaries      # generate a summary from a collection
│   └── learning
│       ├── flashcards
│       └── quizzes
├── db                 # list, backup, restore, export, migrate
├── collections        # list, info, delete, update-path, manage
├── dev                # test, lint, fmt
└── orchestrate
    └── lecture-pipeline
```

Study tools read the **same** collection RAG ingest wrote. After
`corpus tools rag ingest ./docs --collection notes`, flashcards/summaries/quizzes
use `-c notes` (Chroma name `rag_notes`).

## Setup and health

```bash
corpus setup
corpus setup --reset
corpus doctor
corpus doctor --config alt.yaml
corpus benchmark --collection notes --queries 10
```

## RAG

```bash
corpus tools rag ingest ./documents --collection notes
corpus tools rag ingest ./lecture.pdf --collection cs101

corpus tools rag query "What is gradient descent?" --collection notes
corpus tools rag query "explain backprop" -c notes --strategy semantic

corpus tools rag sync --collection notes
corpus tools rag sync ./documents --collection notes
corpus tools rag sync ./docs -c notes --dry-run

corpus tools rag ui
corpus tools rag ui --collection notes
corpus tools rag chat --collection notes
```

Strategies (`hybrid` default, `semantic`, `keyword`) select stages of one
pipeline: vector search, BM25, RRF, optional rerank.

## Video

Requires `pip install corpusrag[video]`.

```bash
corpus tools video ingest lecture.mp4 -c notes
corpus tools video ingest-url "https://youtube.com/watch?v=abc" -c notes
corpus tools video jobs
corpus tools video status <job_id>
```

Visual OCR writes markdown under the output directory. The lecture pipeline
indexes transcripts through RAG ingest (`rag_<collection>`).

## Handwriting

```bash
corpus tools handwriting ingest ./notes-photos -c notes
```

CLI-only (not on MCP).

## Summaries

Requires `pip install corpusrag[generators]`.

```bash
corpus tools summaries -c notes --length medium
corpus tools summaries -c notes --export markdown -o summary.md
```

## Flashcards and quizzes

```bash
corpus tools learning flashcards -c notes --count 15 --difficulty intermediate
corpus tools learning flashcards -c notes --export anki -o cards.apkg

corpus tools learning quizzes -c notes --count 10
```

## Database and collections

```bash
corpus db list
corpus db backup my_collection -o backup.tar.gz
corpus db backup --all -o ./backups/
corpus db restore backup.tar.gz --name new_name --overwrite
corpus db export my_collection -o export.json
corpus db migrate source_collection target_collection

corpus collections list
corpus collections info my_collection
corpus collections delete my_collection
corpus collections update-path my_collection ./new/docs/path
corpus collections manage
```

## Lecture pipeline

```bash
corpus orchestrate lecture-pipeline lecture01.mp4 --course BIOL101 --lecture 1
```

Video path, `--course`, and `--lecture` are required. Counts, summary length,
and cleaning come from `orchestrations.lecture_pipeline` in config unless you
override them with flags.

## MCP

```bash
corpus-mcp-server --profile dev
```

MCP is a **manual subset** of the CLI. See [`mcp-integration.md`](mcp-integration.md).
