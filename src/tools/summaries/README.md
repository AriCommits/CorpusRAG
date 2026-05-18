# Summaries Tool

Generate multi-length summaries from RAG collections with Markdown export.

## CLI Commands

```bash
corpus tools summaries generate -c <collection> --length medium
corpus tools summaries generate -c <collection> --export markdown -o summary.md
```

## Features

- **Length control**: short, medium, long summary generation
- **Collection-aware**: Summarizes content from any RAG collection
- **Export formats**: Markdown, plain text
- **LLM-powered**: Uses configured LLM backend for generation

## Architecture

```
summaries/
├── cli.py         # Click CLI commands
├── generator.py   # Summary generation logic
├── export.py      # Export to various formats
└── config.py      # Summary-specific configuration
```

## Requirements

```bash
pip install corpusrag[generators]
```
