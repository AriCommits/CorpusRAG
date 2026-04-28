# Plan 12: Slim Docker Image + Setup Wizard Docker Integration

**Status:** Not Started
**Created:** 2026-04-27
**Goal:** (A) Reduce Docker image from ~4 GB to ~800 MB by excluding torch/CUDA/ffmpeg from the production image. (B) Add Docker Compose generation to the setup wizard when user selects HTTP ChromaDB mode.

---

## Problem A: Docker Image Bloat

The production Dockerfile runs `pip install ./app` which installs ALL dependencies including:
- `sentence-transformers` → pulls `torch` (530 MB) → pulls CUDA toolkit (~2 GB)
- `ffmpeg` + `build-essential` in base stage (~40 MB + compile toolchain)

The MCP server doesn't need any of this — it calls Ollama/OpenAI over HTTP for embeddings and LLM. The torch/CUDA stack is only needed if you're running sentence-transformers locally, which Docker deployments never do.

## Problem B: Setup Wizard Doesn't Help with Docker

When a user selects "HTTP (Docker Server)" for ChromaDB, the wizard just saves the config and hopes the user figures out Docker on their own. It should offer to generate a minimal `docker-compose.yml` and optionally start the containers.

---

## Tasks

### T1: Create slim pyproject extra and Dockerfile

**Files:** `pyproject.toml`, `.docker/Dockerfile`

Add a `server` extra to pyproject.toml that includes only what the MCP server needs (no torch, no sentence-transformers, no faster-whisper):

```toml
[project.optional-dependencies]
server = [
  "fastapi>=0.116.0",
  "uvicorn>=0.35.0",
  "chromadb>=1.0.20",
  "httpx>=0.27.0",
  "python-dotenv>=1.0.1",
  "pyyaml>=6.0.2",
  "pypdf>=5.1.0",
  "click>=8.1.0",
  "ollama>=0.4.0",
  "mcp[cli]>=1.20.0",
  "langchain>=0.3.0",
  "langchain-community>=0.3.0",
  "langchain-chroma>=0.2.0",
  "keyring>=25.0.0",
  "cryptography>=41.0.0",
  "rank_bm25>=0.2.2",
  "rich>=13.7.0",
  "langchain-core>=0.3.0",
  "langchain-text-splitters>=0.3.0",
]
```

Then update the Dockerfile production stage:
- Remove `ffmpeg` and `build-essential` from base (move to a `full` stage)
- Split into `base-slim` (curl, git, poppler-utils only) and `base-full`
- Production stage uses `pip install --user --no-cache-dir "./app[server]"`
- Development stage keeps `"./app[full,dev]"`

### T2: Add Docker Compose generation to setup wizard

**Files:** `src/setup_wizard.py`

When user selects HTTP mode in ChromaScreen and proceeds, add a new screen (or extend the flow) that:
1. Asks "Would you like to generate a docker-compose.yml for ChromaDB?"
2. If yes, writes a minimal compose file to `.docker/docker-compose.yml`:
   ```yaml
   services:
     chromadb:
       image: chromadb/chroma:latest
       ports:
         - "8001:8000"
       volumes:
         - chroma-data:/chroma/chroma
   volumes:
     chroma-data:
   ```
3. Asks "Start ChromaDB now? (requires Docker)" 
4. If yes, runs `docker compose -f .docker/docker-compose.yml up -d chromadb`
5. Updates the config with `host: localhost`, `port: 8001`

### T3: Add tests

**Files:** `tests/unit/test_docker_slim.py` (NEW), update `tests/unit/test_setup_wizard_config.py`

- Test that `server` extra exists in pyproject.toml and doesn't include torch/sentence-transformers
- Test that setup wizard generates docker-compose.yml when HTTP mode selected
- Test that generated compose file is valid YAML with chromadb service

---

## File Dependency Matrix

```
                         │ T1   T2   T3
─────────────────────────┼───────────────
pyproject.toml           │ ██
.docker/Dockerfile       │ ██
src/setup_wizard.py      │      ██
tests/unit/test_docker*  │           ██
tests/unit/test_setup*   │           ██
```

T1 and T2 modify different files → **can run in parallel**.
T3 depends on both T1 and T2.

---

## Done When

- [ ] `pip install corpusrag[server]` installs without torch/sentence-transformers
- [ ] Docker image built with `[server]` extra is < 1 GB
- [ ] Setup wizard offers Docker Compose generation for HTTP mode
- [ ] Generated compose file starts ChromaDB successfully
- [ ] All tests pass
