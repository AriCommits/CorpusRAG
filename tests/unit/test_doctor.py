"""Tests for corpus doctor persistent vs HTTP Chroma checks."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from config.base import BaseConfig, DatabaseConfig
from tools.rag.doctor import run_doctor


def _config(tmp_path: Path, mode: str = "persistent") -> BaseConfig:
    cfg = BaseConfig()
    cfg.database = DatabaseConfig(
        mode=mode,
        host="localhost",
        port=8001,
        persist_directory=tmp_path / "chroma",
    )
    cfg.llm.endpoint = "http://127.0.0.1:9"
    cfg.llm.model = "test-model"
    cfg.embedding.model = "embed-test"
    return cfg


def test_persistent_doctor_does_not_http_heartbeat(tmp_path: Path) -> None:
    cfg = _config(tmp_path, mode="persistent")
    with (
        patch("tools.rag.doctor.ChromaDBBackend") as mock_db_cls,
        patch("tools.rag.doctor.httpx.get", side_effect=ConnectionError("ollama")) as mock_get,
    ):
        mock_db_cls.return_value.list_collections.return_value = ["rag_notes"]
        results = run_doctor(cfg)

    chroma_ok = [msg for passed, msg in results if passed and "persistent store" in msg]
    assert chroma_ok
    mock_db_cls.assert_called_once()
    for call in mock_get.call_args_list:
        assert "heartbeat" not in str(call.args[0])


def test_http_doctor_probes_v2_heartbeat_when_down(tmp_path: Path) -> None:
    cfg = _config(tmp_path, mode="http")
    with patch("tools.rag.doctor.httpx.get", side_effect=ConnectionError("refused")):
        results = run_doctor(cfg)
    chroma_fail = [msg for passed, msg in results if not passed and "ChromaDB unreachable" in msg]
    assert chroma_fail


def test_http_doctor_lists_collections_when_heartbeat_ok(tmp_path: Path) -> None:
    cfg = _config(tmp_path, mode="http")

    def fake_get(url, **kwargs):
        resp = MagicMock()
        if "heartbeat" in url:
            resp.status_code = 200
            return resp
        raise ConnectionError("ollama down")

    with (
        patch("tools.rag.doctor.httpx.get", side_effect=fake_get) as mock_get,
        patch("tools.rag.doctor.ChromaDBBackend") as mock_db_cls,
    ):
        mock_db_cls.return_value.list_collections.return_value = []
        results = run_doctor(cfg)
    mock_get.assert_any_call("http://localhost:8001/api/v2/heartbeat", timeout=5)
    assert any(p and "ChromaDB reachable" in m for p, m in results)
