"""SQLite-based execution telemetry for time estimation."""

import functools
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


class TelemetryStore:
    """Persistent SQLite store for tool execution telemetry."""

    def __init__(self, db_path: str = ".corpusrag/telemetry.db", enabled: bool = True):
        self.enabled = enabled
        self.db_path = db_path
        self._lock = threading.Lock()
        if enabled:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._create_table()
        else:
            self._conn = None

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                input_size_bytes INTEGER DEFAULT 0,
                output_summary TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                success INTEGER DEFAULT 1
            )
        """)
        self._conn.commit()

    def log(self, tool_name: str, duration_ms: float, input_size: int = 0,
            output_summary: str = "", metadata: dict | None = None, success: bool = True) -> None:
        if not self.enabled or not self._conn:
            return
        with self._lock:
            self._conn.execute(
                "INSERT INTO tool_executions (tool_name, started_at, duration_ms, input_size_bytes, output_summary, metadata_json, success) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tool_name, datetime.now(timezone.utc).isoformat(), duration_ms, input_size,
                 output_summary, json.dumps(metadata or {}), int(success))
            )
            self._conn.commit()

    def get_estimates(self, tool_name: str, limit: int = 50) -> dict:
        if not self.enabled or not self._conn:
            return {}
        rows = self._conn.execute(
            "SELECT duration_ms FROM tool_executions WHERE tool_name = ? AND success = 1 ORDER BY id DESC LIMIT ?",
            (tool_name, limit)
        ).fetchall()
        if not rows:
            return {}
        durations = sorted([r["duration_ms"] for r in rows])
        n = len(durations)
        return {
            "tool": tool_name,
            "avg_ms": round(sum(durations) / n, 2),
            "p50_ms": round(durations[n // 2], 2),
            "p95_ms": round(durations[int(n * 0.95)], 2),
            "sample_count": n,
        }

    def _validate_sql(self, sql: str) -> str:
        import re
        stripped = sql.strip()
        if not stripped.upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")
        if ";" in stripped:
            raise ValueError("Multiple statements not allowed")
        if "--" in stripped or "/*" in stripped:
            raise ValueError("SQL comments not allowed")
        _BLOCKED = {"ATTACH", "DETACH", "LOAD_EXTENSION", "PRAGMA", "INSERT",
                    "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "UNION", "INTO"}
        tokens = set(re.findall(r'\b[A-Z_]+\b', stripped.upper()))
        blocked = tokens & _BLOCKED
        if blocked:
            raise ValueError(f"Blocked SQL keywords: {blocked}")
        return stripped

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        if not self.enabled or not self._conn:
            return []
        validated = self._validate_sql(sql)
        rows = self._conn.execute(validated, params).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


def timed(store: TelemetryStore, tool_name: str):
    """Decorator that measures and logs execution time."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                store.log(tool_name, duration, success=True)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                store.log(tool_name, duration, success=False, output_summary=str(e))
                raise
        return wrapper
    return decorator


_global_store: TelemetryStore | None = None


def init_telemetry(db_path: str = ".corpusrag/telemetry.db", enabled: bool = True) -> TelemetryStore:
    global _global_store
    _global_store = TelemetryStore(db_path, enabled)
    return _global_store


def get_telemetry_store() -> TelemetryStore | None:
    return _global_store
