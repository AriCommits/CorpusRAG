# Sprint 2 — Tests (Serial)

**Plan:** docs/plans/plan_12/plan.md
**Wave:** 2 of 2
**Can run in parallel with:** none — needs T1 and T2 complete
**Must complete before:** nothing (final wave)

---

## Agent A: T3 — Add Tests

**Complexity:** S
**Estimated time:** 30 min
**Files to modify:**
- `tests/unit/test_docker_slim.py` (NEW)
- `tests/unit/test_setup_wizard_config.py` (add Docker compose test)

**Depends on:** T1, T2
**Blocks:** none

**Instructions:**

1. Create `tests/unit/test_docker_slim.py`:
```python
"""Tests for Docker image slimming — verify server extra exists."""
import pytest

class TestServerExtra:
    def test_server_extra_in_pyproject(self):
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        extras = data["project"]["optional-dependencies"]
        assert "server" in extras

    def test_server_extra_excludes_torch(self):
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        server_deps = data["project"]["optional-dependencies"]["server"]
        dep_names = [d.split(">=")[0].split("<")[0].strip().lower() for d in server_deps]
        assert "torch" not in dep_names
        assert "sentence-transformers" not in dep_names
        assert "faster-whisper" not in dep_names
```

2. Add to `tests/unit/test_setup_wizard_config.py`:
```python
def test_http_mode_generates_docker_compose(self, wizard):
    wizard.wizard_config.chroma_mode = "http"
    wizard.wizard_config.chroma_port = 8001
    wizard.save_config()
    compose_file = Path(".docker/docker-compose.yml")
    assert compose_file.exists()
    config = yaml.safe_load(open(compose_file))
    assert "services" in config
    assert "chromadb" in config["services"]

def test_persistent_mode_no_docker_compose(self, wizard):
    wizard.wizard_config.chroma_mode = "persistent"
    wizard.save_config()
    compose_file = Path(".docker/docker-compose.yml")
    assert not compose_file.exists()
```

**Definition of Done:**
- [ ] `tests/unit/test_docker_slim.py` passes (server extra exists, no torch)
- [ ] Docker compose generation tests pass
- [ ] All existing tests still pass
