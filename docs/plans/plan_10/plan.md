# Plan 10: Fix Incomplete Config Generation in Setup Wizard

**Status:** Not Started
**Created:** 2026-04-27
**Goal:** Make `corpus setup` generate a complete, working `configs/base.yaml` that includes all required sections — especially `rag`, `embedding.backend`, and sensible defaults. Telemetry should default to disabled. The generated config should work out of the box with `corpus rag ingest` without manual editing.

---

## Problem

The setup wizard (`src/setup_wizard.py`) generates an incomplete config. Its `save_config()` method only writes:

```yaml
llm:
  backend: ollama
  model: gemma4:26b-a4b-it-q4_K_M
embedding:
  model: embeddinggemma
database:
  mode: persistent
paths:
  vault: ./vault
telemetry:
  enabled: false    # or true if user opted in
```

**Missing sections that cause failures:**

| Missing Field | What Breaks | Default Needed |
|---------------|-------------|----------------|
| `llm.endpoint` | LLM backend can't connect | `http://localhost:11434` |
| `llm.timeout_seconds` | No timeout set | `120.0` |
| `llm.temperature` | No temperature | `0.7` |
| `embedding.backend` | Embedding client doesn't know which backend | `ollama` |
| `database.persist_directory` | ChromaDB doesn't know where to store | `./chroma_store` |
| `database.backend` | DB layer doesn't know which backend | `chromadb` |
| `rag` (entire section) | `RAGConfig.from_dict()` gets empty dict, uses code defaults but `parent_store.path` isn't created | Full rag section |
| `rag.strategy` | No retrieval strategy selected | `hybrid` |
| `rag.chunking` | Uses code defaults (800/100) but not explicit | `child_chunk_size: 400, child_chunk_overlap: 50` |
| `rag.parent_store.path` | Parent docs stored in default `./parent_store` which may not exist | `./parent_store` |
| `rag.collection_prefix` | Uses code default `rag` but not explicit | `rag` |

The code defaults in `RAGConfig` dataclass do fill in most values at runtime, but:
1. The config file looks incomplete to users who open it
2. `parent_store` directory isn't created
3. `embedding.backend` is genuinely missing (not defaulted anywhere)
4. Users who choose OpenAI/Anthropic backend don't get `api_key` or `endpoint` fields

---

## Solution

Modify `save_config()` to generate a complete config with all sections. Use the existing `RAGConfig` dataclass defaults as the source of truth. Also fix the `WizardConfig` dataclass to carry endpoint/api_key info for non-Ollama backends.

---

## Tasks

### T1: Update `WizardConfig` dataclass to carry full config state

**File:** `src/setup_wizard.py` (lines 27-36)

Add fields for the missing config values:

```python
@dataclass
class WizardConfig:
    """Configuration collected during wizard."""
    # LLM
    llm_backend: str = "ollama"
    llm_endpoint: str = "http://localhost:11434"
    llm_model: str = "gemma4:26b-a4b-it-q4_K_M"
    llm_api_key: str | None = None
    # Embedding
    embedding_backend: str = "ollama"
    embedding_model: str = "embeddinggemma"
    # Database
    chroma_mode: str = "persistent"
    chroma_host: str | None = None
    chroma_port: int = 8000
    # Paths
    vault_path: str = "./vault"
    # RAG
    rag_strategy: str = "hybrid"
    # Telemetry
    telemetry_enabled: bool = False  # Default OFF
```

- [ ] Add `llm_endpoint`, `llm_api_key`, `embedding_backend`, `chroma_port`, `rag_strategy`
- [ ] Ensure `telemetry_enabled` defaults to `False`

### T2: Update `BackendScreen` to set endpoint/api_key based on backend choice

**File:** `src/setup_wizard.py` (BackendScreen class)

When user selects a backend, set appropriate defaults:

- **ollama**: endpoint = `http://localhost:11434`, api_key = None
- **openai**: endpoint = `https://api.openai.com/v1`, prompt for api_key
- **anthropic**: endpoint = `https://api.anthropic.com`, prompt for api_key

- [ ] Update `on_button_pressed` to set `llm_endpoint` based on backend
- [ ] Add an API key input field that shows only for openai/anthropic
- [ ] Set `embedding_backend` to match `llm_backend` (ollama uses ollama embeddings, openai uses openai embeddings)

### T3: Rewrite `save_config()` to generate complete config

**File:** `src/setup_wizard.py` (save_config method, ~line 425)

Replace the current partial config generation with a complete one:

```python
def save_config(self) -> bool:
    try:
        base_config_path = Path("configs/base.yaml")
        base_config_path.parent.mkdir(parents=True, exist_ok=True)

        wc = self.wizard_config

        config = {
            "llm": {
                "backend": wc.llm_backend,
                "endpoint": wc.llm_endpoint,
                "model": wc.llm_model,
                "timeout_seconds": 120.0,
                "temperature": 0.7,
                "max_tokens": None,
                "api_key": wc.llm_api_key,
                "fallback_models": [],
                "rate_limit_rpm": None,
                "rate_limit_concurrent": None,
            },
            "embedding": {
                "backend": wc.embedding_backend,
                "model": wc.embedding_model,
                "dimensions": None,
            },
            "database": {
                "backend": "chromadb",
                "mode": wc.chroma_mode,
                "host": wc.chroma_host or "localhost",
                "port": wc.chroma_port,
                "persist_directory": "./chroma_store",
            },
            "paths": {
                "vault": wc.vault_path.replace("\\", "/"),
                "scratch_dir": "./scratch",
                "output_dir": "./output",
            },
            "rag": {
                "strategy": wc.rag_strategy,
                "chunking": {
                    "child_chunk_size": 400,
                    "child_chunk_overlap": 50,
                },
                "retrieval": {
                    "top_k_semantic": 50,
                    "top_k_bm25": 50,
                    "top_k_final": 25,
                    "rrf_k": 80,
                },
                "parent_store": {
                    "type": "local_file",
                    "path": "./parent_store",
                },
                "collection_prefix": "rag",
            },
            "telemetry": {
                "enabled": False,  # Always default to disabled
            },
        }

        # Only include telemetry enabled if user opted in
        if wc.telemetry_enabled:
            config["telemetry"]["enabled"] = True

        with open(base_config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Create required directories
        Path("./parent_store").mkdir(parents=True, exist_ok=True)
        Path("./chroma_store").mkdir(parents=True, exist_ok=True)
        Path(wc.vault_path).mkdir(parents=True, exist_ok=True)

        return True
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return False
```

- [ ] Generate all sections: `llm`, `embedding`, `database`, `paths`, `rag`, `telemetry`
- [ ] Include `rag.strategy`, `rag.chunking`, `rag.retrieval`, `rag.parent_store`, `rag.collection_prefix`
- [ ] Create `parent_store/` and `chroma_store/` directories
- [ ] Telemetry defaults to `False` (only `True` if user explicitly opted in)
- [ ] Ensure `configs/` directory exists before writing

### T4: Add tests

**File:** `tests/unit/test_setup_wizard_config.py` (NEW)

```python
"""Tests for setup wizard config generation."""

import yaml
import pytest
from pathlib import Path


@pytest.fixture()
def wizard(tmp_path, monkeypatch):
    """Create a wizard instance with tmp paths."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "configs").mkdir()

    from setup_wizard import SetupWizardApp
    w = SetupWizardApp()
    w.wizard_config.vault_path = str(tmp_path / "vault")
    return w


class TestSaveConfig:
    def test_generates_complete_config(self, wizard):
        assert wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))

        # All top-level sections present
        for section in ["llm", "embedding", "database", "paths", "rag", "telemetry"]:
            assert section in config, f"Missing section: {section}"

    def test_rag_section_complete(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        rag = config["rag"]

        assert "strategy" in rag
        assert "chunking" in rag
        assert "retrieval" in rag
        assert "parent_store" in rag
        assert "collection_prefix" in rag
        assert rag["chunking"]["child_chunk_size"] > 0
        assert rag["chunking"]["child_chunk_overlap"] >= 0

    def test_telemetry_defaults_disabled(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert config["telemetry"]["enabled"] is False

    def test_embedding_backend_present(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert "backend" in config["embedding"]

    def test_creates_required_directories(self, wizard, tmp_path):
        wizard.save_config()
        assert Path("parent_store").exists()
        assert Path("chroma_store").exists()
        assert Path(wizard.wizard_config.vault_path).exists()

    def test_openai_backend_sets_endpoint(self, wizard):
        wizard.wizard_config.llm_backend = "openai"
        wizard.wizard_config.llm_endpoint = "https://api.openai.com/v1"
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert config["llm"]["endpoint"] == "https://api.openai.com/v1"
```

- [ ] Test complete config generation
- [ ] Test RAG section is present and valid
- [ ] Test telemetry defaults to disabled
- [ ] Test embedding.backend is present
- [ ] Test directories are created
- [ ] Test non-Ollama backends get correct endpoint

---

## Files Changed

| File | Action |
|------|--------|
| `src/setup_wizard.py` | MODIFY — WizardConfig, BackendScreen, save_config() |
| `tests/unit/test_setup_wizard_config.py` | NEW — tests |

---

## Verification

```bash
# Tests pass
pytest tests/unit/test_setup_wizard_config.py -v

# Generated config is valid YAML with all sections
python -c "
import yaml
from pathlib import Path
# Simulate what save_config generates
from setup_wizard import SetupWizardApp
w = SetupWizardApp()
Path('configs').mkdir(exist_ok=True)
w.save_config()
config = yaml.safe_load(open('configs/base.yaml'))
required = ['llm', 'embedding', 'database', 'paths', 'rag', 'telemetry']
for s in required:
    assert s in config, f'Missing: {s}'
assert config['telemetry']['enabled'] is False
assert 'strategy' in config['rag']
assert 'backend' in config['embedding']
print('PASS: Config is complete')
"
```

---

## Done When

- [ ] `corpus setup` generates a config with all 6 top-level sections
- [ ] `rag` section includes strategy, chunking, retrieval, parent_store, collection_prefix
- [ ] `embedding.backend` is always present
- [ ] Telemetry defaults to disabled
- [ ] `parent_store/`, `chroma_store/`, and vault directories are created
- [ ] Non-Ollama backends get appropriate endpoint and api_key fields
- [ ] Tests pass
- [ ] Existing tests still pass
