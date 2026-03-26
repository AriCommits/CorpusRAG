# src/homeschool/transaction.py

import sqlite3
import uuid
import time
import structlog
from enum import Enum
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from src.homeschool.config import load

cfg = load()
log = structlog.get_logger()

class TxStatus(str, Enum):
    RUNNING  = "running"
    COMPLETE = "complete"
    FAILED   = "failed"


def _get_conn() -> sqlite3.Connection:
    db_path = cfg.paths.manifest_dir / "manifest.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # isolation_level=None = manual transaction control via BEGIN/COMMIT/ROLLBACK
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")    # Write-Ahead Logging — safer for concurrent readers
    conn.execute("PRAGMA synchronous=NORMAL")  # Good durability/performance tradeoff
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_transactions (
            tx_id        TEXT PRIMARY KEY,
            vault_path   TEXT NOT NULL,
            status       TEXT NOT NULL,
            files_total  INTEGER,
            files_done   INTEGER DEFAULT 0,
            started_at   TEXT,
            updated_at   TEXT,
            duration_sec REAL,
            error        TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indexed_files (
            path         TEXT PRIMARY KEY,
            vault        TEXT NOT NULL,
            mtime        REAL,
            content_hash TEXT,
            indexed_at   TEXT,
            tx_id        TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_errors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id       TEXT NOT NULL,
            vault       TEXT NOT NULL,
            path        TEXT NOT NULL,
            error       TEXT,
            occurred_at TEXT
        )
    """)
    conn.commit()
    return conn


@contextmanager
def sync_transaction(vault_path: str, files_total: int):
    conn    = _get_conn()
    tx_id   = str(uuid.uuid4())
    started = time.monotonic()
    now     = datetime.now().isoformat()

    # Bind tx_id to all log calls within this context automatically
    structlog.contextvars.bind_contextvars(tx_id=tx_id[:8], vault=Path(vault_path).name)

    conn.execute("BEGIN")
    conn.execute("""
        INSERT INTO sync_transactions
            (tx_id, vault_path, status, files_total, started_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (tx_id, vault_path, TxStatus.RUNNING, files_total, now, now))
    conn.execute("COMMIT")

    log.info("transaction_opened", files_total=files_total)

    tx = _Transaction(conn, tx_id, vault_path)
    try:
        yield tx

        duration = round(time.monotonic() - started, 2)
        conn.execute("BEGIN")
        conn.execute("""
            UPDATE sync_transactions
            SET status = ?, updated_at = ?, duration_sec = ?
            WHERE tx_id = ?
        """, (TxStatus.COMPLETE, datetime.now().isoformat(), duration, tx_id))
        conn.execute("COMMIT")

        log.info("transaction_complete",
                 files_done=tx._files_done,
                 files_errored=tx._files_errored,
                 duration_seconds=duration)

    except Exception as e:
        # Attempt rollback of any open SQLite transaction
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass  # nothing open to roll back

        duration = round(time.monotonic() - started, 2)
        conn.execute("BEGIN")
        conn.execute("""
            UPDATE sync_transactions
            SET status = ?, error = ?, updated_at = ?, duration_sec = ?
            WHERE tx_id = ?
        """, (TxStatus.FAILED, str(e), datetime.now().isoformat(), duration, tx_id))
        conn.execute("COMMIT")

        log.error("transaction_failed",
                  error=str(e),
                  files_done=tx._files_done,
                  files_errored=tx._files_errored,
                  duration_seconds=duration,
                  exc_info=True)
        raise

    finally:
        structlog.contextvars.unbind_contextvars("tx_id", "vault")
        conn.close()


class _Transaction:
    def __init__(self, conn: sqlite3.Connection, tx_id: str, vault_path: str):
        self._conn          = conn
        self.tx_id          = tx_id
        self.vault_path     = vault_path
        self._files_done    = 0
        self._files_errored = 0

    def mark_file_done(self, path: Path, content_hash: str):
        """
        Each file gets its own BEGIN/COMMIT so it's durable immediately.
        This is intentional — it's your recovery checkpoint.
        """
        now = datetime.now().isoformat()
        self._conn.execute("BEGIN")
        self._conn.execute("""
            INSERT OR REPLACE INTO indexed_files
                (path, vault, mtime, content_hash, indexed_at, tx_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(path), self.vault_path, path.stat().st_mtime, content_hash, now, self.tx_id))
        self._conn.execute("""
            UPDATE sync_transactions
            SET files_done = files_done + 1, updated_at = ?
            WHERE tx_id = ?
        """, (now, self.tx_id))
        self._conn.execute("COMMIT")
        self._files_done += 1

        log.debug("file_indexed", file=path.name)

    def mark_file_error(self, path: Path, error: Exception):
        """
        Log the error durably but don't abort the transaction —
        continue processing remaining files.
        """
        now = datetime.now().isoformat()
        self._conn.execute("BEGIN")
        self._conn.execute("""
            INSERT INTO file_errors (tx_id, vault, path, error, occurred_at)
            VALUES (?, ?, ?, ?, ?)
        """, (self.tx_id, self.vault_path, str(path), str(error), now))
        self._conn.execute("COMMIT")
        self._files_errored += 1

        log.warning("file_error", file=path.name, error=str(error), exc_info=True)