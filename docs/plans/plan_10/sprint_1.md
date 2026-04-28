# Sprint 1 — Fix Setup Wizard Config Generation (Serial)

**Plan:** docs/plans/plan_10/plan.md
**Wave:** 1 of 1
**Can run in parallel with:** none — all tasks modify `src/setup_wizard.py`
**Must complete before:** nothing (final sprint)

---

## Why This Is a Single Sprint

All 4 tasks modify or directly depend on `src/setup_wizard.py`. There is no file-level independence to exploit. Running T2 and T3 in parallel would cause merge conflicts on the same file. The correct approach is one agent executing T1 → T2 → T3 → T4 sequentially, committing after each.

---

## Agent A: T1 — Update WizardConfig Dataclass

**Complexity:** S
**Estimated time:** 15 min
**Files to modify:**
- `src/setup_wizard.py` — expand `WizardConfig` dataclass (lines ~27-36)

**Depends on:** none
**Blocks:** T2, T3, T4

**Instructions:**
Find the `WizardConfig` dataclass at the top of `setup_wizard.py`. Add these fields:

```python
@dataclass
class WizardConfig:
    llm_backend: str = "ollama"
    llm_endpoint: str = "http://localhost:11434"
    llm_model: str = "gemma4:26b-a4b-it-q4_K_M"
    llm_api_key: str | None = None
    embedding_backend: str = "ollama"
    embedding_model: str = "embeddinggemma"
    chroma_mode: str = "persistent"
    chroma_host: str | None = None
    chroma_port: int = 8000
    vault_path: str = "./vault"
    rag_strategy: str = "hybrid"
    telemetry_enabled: bool = False
```

Do not change any Screen classes or methods yet.

**Definition of Done:**
- [ ] `WizardConfig` has all 12 fields listed above
- [ ] `telemetry_enabled` defaults to `False`
- [ ] Existing tests still pass (dataclass is backward-compatible — new fields have defaults)

---

## Agent A: T2 — Update BackendScreen for Endpoint/API Key

**Complexity:** M
**Estimated time:** 30 min
**Files to modify:**
- `src/setup_wizard.py` — `BackendScreen` class

**Depends on:** T1
**Blocks:** T4

**Instructions:**
In `BackendScreen.on_button_pressed`, after setting `llm_backend`, also set `llm_endpoint` and `embedding_backend` based on the selection:

- `ollama` → endpoint `http://localhost:11434`, embedding_backend `ollama`
- `openai` → endpoint `https://api.openai.com/v1`, embedding_backend `openai`
- `anthropic` → endpoint `https://api.anthropic.com`, embedding_backend `anthropic`

Optionally add an `Input` widget for API key that's only relevant for openai/anthropic. If too complex for the TUI flow, just set `llm_api_key = None` and add a comment in the generated config telling users to fill it in.

**Definition of Done:**
- [ ] Selecting "OpenAI" sets `llm_endpoint` to `https://api.openai.com/v1`
- [ ] Selecting "Anthropic" sets `llm_endpoint` to `https://api.anthropic.com`
- [ ] `embedding_backend` matches `llm_backend`
- [ ] Existing tests still pass

---

## Agent A: T3 — Rewrite save_config() for Complete Output

**Complexity:** M
**Estimated time:** 30 min
**Files to modify:**
- `src/setup_wizard.py` — `save_config()` method

**Depends on:** T1
**Blocks:** T4

**Instructions:**
Replace the current `save_config()` body with the complete config generation from the plan. The new method must:

1. Create `configs/` directory if missing
2. Build a complete dict with all 6 sections: `llm`, `embedding`, `database`, `paths`, `rag`, `telemetry`
3. Use `self.wizard_config` fields for user choices, hardcode sensible defaults for everything else
4. Write with `yaml.dump(..., default_flow_style=False, sort_keys=False)`
5. Create `parent_store/`, `chroma_store/`, and vault directories
6. Telemetry `enabled` is always `False` unless user explicitly opted in

See the plan's T3 section for the exact config dict structure.

**Definition of Done:**
- [ ] Generated `configs/base.yaml` has all 6 top-level sections
- [ ] `rag` section has `strategy`, `chunking`, `retrieval`, `parent_store`, `collection_prefix`
- [ ] `embedding.backend` is present
- [ ] `telemetry.enabled` is `False` by default
- [ ] `parent_store/`, `chroma_store/`, vault directories are created
- [ ] Existing tests still pass

---

## Agent A: T4 — Add Tests

**Complexity:** S
**Estimated time:** 30 min
**Files to modify:**
- `tests/unit/test_setup_wizard_config.py` (NEW)

**Depends on:** T1, T3
**Blocks:** none

**Instructions:**
Create the test file from the plan's T4 section. Use `monkeypatch.chdir(tmp_path)` to isolate filesystem operations. The fixture creates a `SetupWizardApp`, sets `vault_path` to a tmp dir, and calls `save_config()`. Tests verify:

1. All 6 config sections present
2. RAG section is complete (strategy, chunking, retrieval, parent_store, collection_prefix)
3. Telemetry defaults to disabled
4. `embedding.backend` is present
5. Required directories are created
6. OpenAI backend sets correct endpoint

**Definition of Done:**
- [ ] `tests/unit/test_setup_wizard_config.py` exists with 6 tests
- [ ] All 6 tests pass
- [ ] No regressions in existing tests
