# Sprint 1 — Slim Image + Wizard Docker (Parallel)

**Plan:** docs/plans/plan_12/plan.md
**Wave:** 1 of 2
**Can run in parallel with:** none (first wave)
**Must complete before:** Sprint 2 (T3 tests)

---

## Agent A: T1 — Create `server` Extra and Slim Dockerfile

**Complexity:** M
**Estimated time:** 45 min
**Files to modify:**
- `pyproject.toml` — add `server` optional extra
- `.docker/Dockerfile` — split base into slim/full, use `[server]` for production

**Depends on:** none
**Blocks:** T3

**Instructions:**

1. In `pyproject.toml`, add a new `server` extra under `[project.optional-dependencies]` that lists only the deps needed for the MCP HTTP server. Exclude: `sentence-transformers`, `transformers`, `huggingface-hub`, `textual`, `rich` (TUI-only). Include everything else from the main `dependencies` list. The key insight: the server connects to Ollama/OpenAI over HTTP for embeddings — it doesn't need torch.

2. In `.docker/Dockerfile`, restructure:
   - `base-slim` stage: only `curl git poppler-utils` (no ffmpeg, no build-essential)
   - `production` stage: FROM `base-slim`, install `"./app[server]"`
   - `base-full` stage: FROM `base-slim`, add `ffmpeg build-essential`
   - `development` stage: FROM `base-full`, install `"./app[full,dev]"`
   - `cli` stage: FROM `base-full`, install `"./app[full]"`

**Definition of Done:**
- [ ] `pyproject.toml` has `server` extra without torch/sentence-transformers
- [ ] Dockerfile production stage uses `[server]` extra
- [ ] Dockerfile development stage still uses `[full,dev]`
- [ ] No existing tests broken

---

## Agent B: T2 — Setup Wizard Docker Compose Generation

**Complexity:** M
**Estimated time:** 45 min
**Files to modify:**
- `src/setup_wizard.py` — add Docker compose generation after HTTP mode selection

**Depends on:** none
**Blocks:** T3

**Instructions:**

1. In `setup_wizard.py`, after the `ChromaHostScreen` (when user has selected HTTP mode and entered a host), add logic in `save_config()` to generate a minimal docker-compose file.

2. In `save_config()`, after writing `configs/base.yaml`, add:
```python
if wc.chroma_mode == "http":
    self._generate_docker_compose(wc)
```

3. Add a new method `_generate_docker_compose(self, wc)`:
```python
def _generate_docker_compose(self, wc):
    compose_dir = Path(".docker")
    compose_dir.mkdir(parents=True, exist_ok=True)
    compose_file = compose_dir / "docker-compose.yml"
    
    if compose_file.exists():
        logger.info("docker-compose.yml already exists, skipping generation")
        return
    
    port = wc.chroma_port
    compose = {
        "services": {
            "chromadb": {
                "image": "chromadb/chroma:latest",
                "container_name": "corpus-chromadb",
                "restart": "unless-stopped",
                "ports": [f"{port}:{8000}"],
                "volumes": ["chroma-data:/chroma/chroma"],
            }
        },
        "volumes": {"chroma-data": None},
    }
    
    with open(compose_file, "w") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Generated {compose_file}")
```

4. In the `TestScreen` completion message, add a note about Docker:
```
If you selected HTTP mode, start ChromaDB with:
  docker compose -f .docker/docker-compose.yml up -d
```

**Definition of Done:**
- [ ] Selecting HTTP mode in wizard generates `.docker/docker-compose.yml`
- [ ] Generated file has chromadb service with correct port
- [ ] Existing compose file is NOT overwritten
- [ ] Non-HTTP mode does NOT generate compose file
- [ ] No existing tests broken
