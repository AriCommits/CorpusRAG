# RAG Tool

Retrieval-Augmented Generation pipeline with hybrid search, parent-child chunking, and incremental sync.

## CLI Commands

```bash
corpus tools rag ingest <path> -c <collection>   # Ingest documents
corpus tools rag sync -c <collection>            # Incremental sync (uses stored path)
corpus tools rag sync <path> -c <collection>     # Sync with explicit path
corpus tools rag query "<question>" -c <col>     # One-shot query
corpus tools rag chat -c <collection>            # Interactive CLI chat
corpus tools rag ui                              # TUI (collection picker)
corpus tools rag ui -c <collection>              # TUI with specific collection
```

## Features

- **Hybrid retrieval**: Combines vector similarity (sentence-transformers) with BM25 keyword search
- **Parent-child chunking**: Semantic markdown splitting creates parent docs; child chunks used for search with parent context returned
- **Incremental sync**: Only processes new/modified files; detects deletions
- **Strategy selection**: `hybrid` (default), `semantic`, `keyword`
- **Metadata filtering**: Filter by tags or section headers
- **TUI**: Rich terminal interface with slash commands, context management, collection switching

## TUI Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open Collection Manager |
| `Ctrl+S` | Trigger Sync |
| `Ctrl+H` | Show Help |
| `Ctrl+Q` | Quit |

## Architecture

```
rag/
├── cli.py           # Click CLI commands
├── agent.py         # RAGAgent (query + chat orchestration)
├── ingest.py        # Document ingestion with parent-child architecture
├── sync.py          # Incremental sync engine
├── tui.py           # Textual TUI application
├── tui_collections.py # Collection management TUI screen
├── doctor.py        # Health check diagnostics
├── config.py        # RAG-specific configuration
├── strategies/      # Retrieval strategies (hybrid, semantic, keyword)
└── pipeline/        # Embedding client, parsers, storage
```
