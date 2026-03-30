# CorpusCallosum

CorpusCallosum is a local-first RAG service with:

- one ChromaDB store and many named collections,
- hybrid retrieval (semantic + BM25 + RRF),
- local model generation (Ollama-compatible `/api/generate`),
- API endpoints for ingest, query, critique, flashcards, and collection listing.

## Project layout

```text
src/corpus_callosum/
  __init__.py
  config.py
  ingest.py
  retriever.py
  agent.py
  api.py

configs/
  corpus_callosum.yaml.example

tests/
  test_smoke.py
```

## Requirements

- Python 3.11+
- Local model runner endpoint (default: Ollama at `http://localhost:11434/api/generate`)

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Configuration

Copy the example config:

```bash
cp configs/corpus_callosum.yaml.example configs/corpus_callosum.yaml
```

Config is loaded from:

- `CORPUS_CALLOSUM_CONFIG` environment variable, or
- `configs/corpus_callosum.yaml` by default.

## Running

Start API server:

```bash
PYTHONPATH=src python3 -m corpus_callosum.api
```

Or with installed package script:

```bash
corpus-api
```

### Endpoints

- `GET /health`
- `POST /ingest` body: `{ "file_path": "./vault/bio201", "collection": "bio201" }`
- `POST /query` body: `{ "query": "What is photosynthesis?", "collection": "bio201" }` (SSE stream)
- `POST /critique` body: `{ "essay_text": "..." }` (SSE stream)
- `POST /flashcards` body: `{ "collection": "bio201" }` (SSE stream)
- `GET /collections`

## CLI ingest

```bash
PYTHONPATH=src python3 -m corpus_callosum.ingest --path ./vault/bio201 --collection bio201
```

## Smoke test

```bash
python3 tests/test_smoke.py
```

This test creates a temporary markdown file, ingests it into a test collection, queries it, and prints the streamed response.

## Docker and ChromaDB

This repo includes Docker support for running the API and ChromaDB together.

Files:

- `.docker/Dockerfile` - builds the API container.
- `docker-compose.yml` - runs `corpus_api` + `chroma` services.
- `configs/corpus_callosum.docker.yaml.example` - config template using Chroma HTTP mode.

### Setup

Copy docker config template:

```bash
cp configs/corpus_callosum.docker.yaml.example configs/corpus_callosum.docker.yaml
```

Then start services:

```bash
docker compose up --build
```

### Notes

- Chroma runs at `chroma:8000` inside compose and `localhost:8000` on host.
- API runs at `localhost:8080`.
- Docker config sets:
  - `chroma.mode: http`
  - `chroma.host: chroma`
  - `chroma.port: 8000`
- Model endpoint in the docker config points to host Ollama by default:
  - `http://host.docker.internal:11434/api/generate`
