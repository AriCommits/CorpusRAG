# Video Tool

Video transcription and visual OCR pipeline for extracting knowledge from lectures and presentations.

## CLI Commands

```bash
corpus tools video ingest <file> -c <collection>       # Ingest local video
corpus tools video ingest-url <url> -c <collection>    # Download + ingest from URL
corpus tools video pipeline <directory>                 # Full pipeline on a directory
corpus tools video jobs                                 # List active jobs
corpus tools video status <job_id>                      # Check job status
```

## Features

- **Visual OCR**: Extracts text from slides, chalkboards, whiteboards using vision models
- **Scene detection**: Identifies frame transitions to avoid redundant processing
- **Math extraction**: Optional pix2tex fallback for LaTeX math expressions
- **YouTube support**: Download and process videos from URLs
- **Job management**: Background processing with status tracking
- **Auto-ingest**: Processed text automatically chunked and ingested into RAG collections

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--collection, -c` | Target collection | (required) |
| `--threshold` | Scene detection sensitivity (0.0-1.0) | 0.3 |
| `--model` | Ollama vision model | llava |
| `--no-latex` | Disable pix2tex math fallback | false |
| `--context-window` | Adjacent frames per chunk | 1 |
| `--keep-frames` | Keep extracted frames after ingest | false |

## Architecture

```
video/
├── cli.py           # Click CLI commands
├── ingest.py        # Main ingestion orchestrator
├── download.py      # URL download (yt-dlp)
├── extractor.py     # Frame extraction + scene detection
├── ocr.py           # Vision model OCR
├── postprocessor.py # Text cleanup and deduplication
├── jobs.py          # Job queue management
├── config.py        # Video-specific configuration
└── transcribe.py    # Whisper transcription
```

## Requirements

```bash
pip install corpusrag[video]  # Installs faster-whisper, Pillow, numpy
```

Also requires:
- Ollama with a vision model (`ollama pull llava`)
- ffmpeg on PATH
