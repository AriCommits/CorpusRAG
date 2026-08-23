"""Tests for setup wizard config generation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture()
def wizard(tmp_path, monkeypatch):
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

    def test_telemetry_defaults_disabled(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert config["telemetry"]["enabled"] is False

    def test_embedding_backend_present(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert "backend" in config["embedding"]
        assert config["embedding"]["backend"] == "ollama"

    def test_creates_required_directories(self, wizard):
        wizard.save_config()
        assert Path("parent_store").exists()
        assert Path("chroma_store").exists()
        assert Path(wizard.wizard_config.vault_path).exists()

    def test_openai_backend_sets_endpoint(self, wizard):
        wizard.wizard_config.llm_backend = "openai"
        wizard.wizard_config.llm_endpoint = "https://api.openai.com/v1"
        wizard.wizard_config.embedding_backend = "openai"
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert config["llm"]["endpoint"] == "https://api.openai.com/v1"
        assert config["llm"]["backend"] == "openai"
        assert config["embedding"]["backend"] == "openai"

    def test_llm_section_complete(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        llm = config["llm"]
        assert "endpoint" in llm
        assert "timeout_seconds" in llm
        assert "temperature" in llm
        assert llm["timeout_seconds"] == 120.0

    def test_database_section_complete(self, wizard):
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        db = config["database"]
        assert "backend" in db
        assert "persist_directory" in db
        assert db["backend"] == "chromadb"

    def test_http_default_port_is_8001(self, wizard):
        assert wizard.wizard_config.chroma_port == 8001
        wizard.wizard_config.chroma_mode = "http"
        wizard.save_config()
        config = yaml.safe_load(open("configs/base.yaml"))
        assert config["database"]["port"] == 8001

    def test_http_mode_generates_docker_compose(self, wizard):
        """HTTP mode should generate a docker-compose.yml."""
        wizard.wizard_config.chroma_mode = "http"
        wizard.save_config()
        compose_file = Path(".docker/docker-compose.yml")
        assert compose_file.exists(), "docker-compose.yml not generated for HTTP mode"
        config = yaml.safe_load(open(compose_file))
        assert "services" in config
        assert "chromadb" in config["services"]
        assert "8001:8000" in config["services"]["chromadb"]["ports"]

    def test_persistent_mode_no_docker_compose(self, wizard):
        """Persistent mode should NOT generate docker-compose.yml."""
        wizard.wizard_config.chroma_mode = "persistent"
        wizard.save_config()
        compose_file = Path(".docker/docker-compose.yml")
        assert not compose_file.exists()


def test_launch_rag_tui_passes_agent_and_collection(tmp_path, monkeypatch):
    """Launch helper must construct RAGApp(agent, collection), not RAGApp()."""
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "base.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "llm": {"model": "m"},
                "database": {"mode": "persistent", "persist_directory": str(tmp_path / "c")},
            }
        ),
        encoding="utf-8",
    )
    fake_app = MagicMock()
    with (
        patch("tools.rag.tui.RAGApp", return_value=fake_app) as mock_app_cls,
        patch("tools.rag.agent.RAGAgent") as mock_agent_cls,
        patch("cli_common.load_cli_db") as mock_load,
    ):
        mock_cfg = MagicMock()
        mock_db = MagicMock()
        mock_load.return_value = (mock_cfg, mock_db)
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        from setup_wizard import launch_rag_tui

        launch_rag_tui(str(cfg_file), collection="notes")

    mock_app_cls.assert_called_once_with(mock_agent, "notes")
    fake_app.run.assert_called_once()
