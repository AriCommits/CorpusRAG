"""Focused tests for lazy Chroma loading (Sprint 1 A3).

Covers two behaviours:

* ``db`` eagerly exports :class:`DatabaseBackend` but only imports the heavy
  :class:`ChromaDBBackend` (and its ``chromadb`` dependency) on first access.
* ``cli_common`` no longer imports Chroma at module load time; the import is
  localized inside :func:`cli_common.load_cli_db`.
"""

import importlib
import sys

import pytest


class TestDbLazyExport:
    """The ``db`` package should lazily expose ``ChromaDBBackend``."""

    def test_all_preserved(self) -> None:
        """``__all__`` still advertises both backends."""
        import db

        assert set(db.__all__) == {"ChromaDBBackend", "DatabaseBackend"}

    def test_database_backend_eager(self) -> None:
        """``DatabaseBackend`` is importable directly (eager export)."""
        from db import DatabaseBackend

        assert DatabaseBackend.__name__ == "DatabaseBackend"

    def test_chroma_backend_lazy_accessible(self) -> None:
        """``ChromaDBBackend`` is still reachable via attribute access."""
        import db

        backend = db.ChromaDBBackend
        assert backend.__name__ == "ChromaDBBackend"

    def test_chroma_backend_from_import(self) -> None:
        """``from db import ChromaDBBackend`` continues to work."""
        from db import ChromaDBBackend

        assert ChromaDBBackend.__name__ == "ChromaDBBackend"

    def test_unknown_attribute_raises(self) -> None:
        """Unknown attributes raise ``AttributeError`` as usual."""
        import db

        with pytest.raises(AttributeError):
            _ = db.DoesNotExist

    def test_importing_db_does_not_load_chroma_module(self) -> None:
        """Importing ``db`` must not eagerly import the ``db.chroma`` module."""
        # Drop any previously-imported db modules so we observe a clean import.
        for mod in [m for m in sys.modules if m == "db" or m.startswith("db.")]:
            del sys.modules[mod]

        importlib.import_module("db")

        assert "db.chroma" not in sys.modules, (
            "importing 'db' should not eagerly import 'db.chroma'"
        )


class TestCliCommonLazyImport:
    """``cli_common`` must not import Chroma at module import time."""

    def test_no_module_level_chroma_import(self) -> None:
        """Reloading ``cli_common`` should not pull in ``db.chroma``."""
        for mod in [m for m in sys.modules if m == "db" or m.startswith("db.")]:
            del sys.modules[mod]
        sys.modules.pop("cli_common", None)

        importlib.import_module("cli_common")

        assert "db.chroma" not in sys.modules, (
            "importing 'cli_common' should not eagerly import 'db.chroma'"
        )

    def test_helpers_still_exported(self) -> None:
        """The public CLI helpers remain importable."""
        from cli_common import load_cli_config, load_cli_db

        assert callable(load_cli_config)
        assert callable(load_cli_db)

    def test_load_cli_db_uses_chroma(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``load_cli_db`` constructs a Chroma backend from the loaded config."""
        import cli_common
        import db

        captured: dict[str, object] = {}

        class _Cfg:
            database = {"backend": "chromadb"}

        class FakeChroma:
            def __init__(self, database):  # type: ignore[no-untyped-def]
                captured["database"] = database

        monkeypatch.setattr(cli_common, "load_cli_config", lambda *a, **k: _Cfg())
        # ``load_cli_db`` does ``from db import ChromaDBBackend`` at call time,
        # so patching the attribute on the ``db`` module is sufficient.
        monkeypatch.setattr(db, "ChromaDBBackend", FakeChroma)

        cfg, backend = cli_common.load_cli_db("dummy.yaml")

        assert isinstance(cfg, _Cfg)
        assert isinstance(backend, FakeChroma)
        assert captured["database"] == {"backend": "chromadb"}
