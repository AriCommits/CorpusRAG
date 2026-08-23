# Docker Deployment Guide

Deploy CorpusRAG with Docker Compose. The compose file lives at
`.docker/docker-compose.yml`.

## Quick start

From the repository root:

```bash
cd .docker
docker compose up -d
```

That starts **ChromaDB** and the **MCP server**. Optional profiles:

```bash
docker compose -f .docker/docker-compose.yml --profile ollama up -d
docker compose -f .docker/docker-compose.yml --profile cli up -d
docker compose -f .docker/docker-compose.yml --profile full up -d
```

| Service | Profile | Host port |
|---------|---------|-----------|
| `chromadb` | default | 8001 → container 8000 |
| `corpus-mcp` | default | 8000 |
| `ollama` | `ollama`, `full` | 11434 (localhost only) |
| `corpus-cli` | `cli`, `full` | — (interactive) |

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Ollama        │    │  CorpusRAG       │    │   ChromaDB      │
│   (optional)    │◄───┤  MCP Server      ├───►│   (vector DB)   │
│   :11434        │    │  :8000           │    │   :8001         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

On the host, the usual local workflow is still `corpus setup` then
`corpus tools rag ingest …` against a persistent `./chroma_store`, or HTTP
mode pointing at `localhost:8001`.

## Configuration

Compose sets HTTP Chroma and (when Ollama is up) an in-network LLM endpoint:

```bash
CORPUSRAG_DATABASE_MODE=http
CORPUSRAG_DATABASE_HOST=chromadb
CORPUSRAG_DATABASE_PORT=8000
CORPUSRAG_LLM_ENDPOINT=http://ollama:11434
```

Host-side `CC_*` overrides still work for a local `corpus` CLI talking to
published ports (`CC_DATABASE_HOST=localhost`, `CC_DATABASE_PORT=8001`).

Configs are mounted read-only from `../configs` into the MCP and CLI
containers.

## Run CLI in Compose

```bash
docker compose -f .docker/docker-compose.yml --profile cli run --rm corpus-cli \
  corpus tools rag ingest --path /home/corpus/data/docs --collection notes

docker compose -f .docker/docker-compose.yml exec corpus-mcp \
  corpus db list

docker compose -f .docker/docker-compose.yml exec corpus-mcp \
  corpus db backup notes -o /home/corpus/data/notes.tar.gz
```

Use the nested `corpus tools …` / `corpus db …` commands — there is no
`corpus-rag` or `corpus-db` entry point.

## Health

```bash
curl http://localhost:8001/api/v2/heartbeat   # ChromaDB
curl http://localhost:11434/api/tags          # Ollama, if started
corpus doctor                                 # local CLI against your config
```

The MCP image healthcheck is `.docker/healthcheck.py` inside the container.

## Build

```bash
docker compose -f .docker/docker-compose.yml build
```

Dockerfile: `.docker/Dockerfile` (targets `production` and `cli`).

## Related

- [Architecture](architecture.md)
- [Troubleshooting](troubleshooting.md)
- [README](../README.md)
