# Handwriting Tool

OCR pipeline for handwritten notes using vision models, with intelligent chunking and post-processing.

## CLI Commands

```bash
corpus tools handwriting ingest <path> -c <collection>
```

## Features

- **Vision model OCR**: Uses Ollama vision models to read handwritten text
- **Intelligent chunking**: Splits recognized text into semantically meaningful chunks
- **Post-processing**: Corrects common OCR errors in handwritten text
- **Directory walking**: Recursively processes image directories
- **Format support**: PNG, JPG, JPEG, TIFF, BMP

## Architecture

```
handwriting/
├── cli.py              # Click CLI commands
├── ingest_handwriting.py # Main ingestion orchestrator
├── ocr.py              # Vision model OCR interface
├── walker.py           # Directory traversal + file discovery
├── preprocessor.py     # Image preprocessing (contrast, rotation)
├── postprocessor.py    # Text cleanup and correction
├── corrector.py        # Spelling/grammar correction
├── chunker.py          # Semantic text chunking
└── config.py           # Handwriting-specific configuration
```

## Requirements

```bash
pip install corpusrag[handwriting]  # Installs Pillow, numpy
```

Also requires Ollama with a vision model (`ollama pull llava`).
