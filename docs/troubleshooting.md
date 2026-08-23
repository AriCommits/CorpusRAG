# CorpusRAG Troubleshooting Guide

Start with `corpus doctor`. It checks the database, LLM, and embedding backends
against your config. Persistent mode opens the local Chroma store (no Docker).
HTTP mode probes `http://<host>:<port>/api/v2/heartbeat` — from the host that
is port **8001** when using the repo Compose file.

## Quick checks

```bash
corpus doctor
corpus --help
corpus-mcp-server --help
```

Docker (from repo root):

```bash
docker compose -f .docker/docker-compose.yml ps
docker compose -f .docker/docker-compose.yml logs -f corpus-mcp
docker compose -f .docker/docker-compose.yml logs -f chromadb
```

Connectivity:

```bash
curl http://localhost:8001/api/v2/heartbeat    # ChromaDB published port
curl http://localhost:11434/api/tags           # Ollama
```

## Common issues

### MCP server will not start

- Confirm the config file exists (`configs/base.yaml` or `--config`).
- For HTTP transport, check port 8000 is free.
- In Compose: `docker compose -f .docker/docker-compose.yml logs corpus-mcp`.
- List collections from inside the container:

```bash
docker compose -f .docker/docker-compose.yml exec corpus-mcp corpus db list
```

### Empty or wrong study results

Flashcards, summaries, and quizzes read `rag_<collection>`. Ingest first:

```bash
corpus tools rag ingest ./docs --collection notes
corpus tools learning flashcards -c notes
corpus tools summaries -c notes
```

If you still see “collection does not exist”, you are passing a different
`-c` name than ingest, or looking at an old `flashcards_*` collection.

### Lecture pipeline TypeError / missing transcript

The transcriber takes only a video path. Use:

```bash
corpus orchestrate lecture-pipeline lecture01.mp4 --course BIOL101 --lecture 1
```

Whisper models download into `models/whisper` (or `video.models_dir`).

### Retrieval feels “cross-contaminated”

Parents are per collection under `parent_store/<collection>/`. Old parent JSON
files sitting in the store root (pre-sprint-2) are ignored by BM25. Re-ingest
the collection if keyword search looks empty.

### ChromaDB / embeddings

```bash
corpus tools rag ingest ./data --collection test
corpus tools rag query "smoke test" -c test
```

HTTP mode must match Compose: host `localhost`, port **8001** from the host
(container listens on 8000). Persistent mode uses `./chroma_store`.

### Backup and restore

```bash
corpus db list
corpus db backup notes -o backups/notes.tar.gz
corpus db backup --all -o ./backups/
corpus db restore backups/notes.tar.gz --name notes_restored
```

In Compose, exec `corpus db …` on `corpus-mcp` or `corpus-cli`. There is no
`corpus-db` binary.

### Logs

Local runs print to stderr. Compose: `docker compose -f .docker/docker-compose.yml logs`.
There is no `corpus-callosum` systemd unit.
