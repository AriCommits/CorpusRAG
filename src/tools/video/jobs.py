"""Async job manager for long-running video pipelines."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class JobState:
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress_pct: int = 0
    current_step: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress_pct": self.progress_pct,
            "current_step": self.current_step,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class JobManager:
    def __init__(self, max_workers: int = 2, expiry_seconds: int = 3600):
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()
        self._expiry = timedelta(seconds=expiry_seconds)

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> str:
        job_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._jobs[job_id] = JobState(job_id=job_id)

        def _run():
            with self._lock:
                self._jobs[job_id].status = JobStatus.RUNNING
                self._jobs[job_id].updated_at = datetime.now()

            def progress_cb(pct: int, step: str = ""):
                with self._lock:
                    self._jobs[job_id].progress_pct = pct
                    self._jobs[job_id].current_step = step
                    self._jobs[job_id].updated_at = datetime.now()

            try:
                result = fn(progress_cb, *args, **kwargs)
                with self._lock:
                    self._jobs[job_id].status = JobStatus.COMPLETE
                    self._jobs[job_id].progress_pct = 100
                    self._jobs[job_id].result = result
                    self._jobs[job_id].updated_at = datetime.now()
            except Exception as e:
                with self._lock:
                    self._jobs[job_id].status = JobStatus.FAILED
                    self._jobs[job_id].error = str(e)
                    self._jobs[job_id].updated_at = datetime.now()

        self._pool.submit(_run)
        return job_id

    def get_status(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobState]:
        self._cleanup_expired()
        with self._lock:
            return list(self._jobs.values())

    def _cleanup_expired(self):
        now = datetime.now()
        with self._lock:
            expired = [
                jid for jid, state in self._jobs.items()
                if state.status in (JobStatus.COMPLETE, JobStatus.FAILED)
                and now - state.updated_at > self._expiry
            ]
            for jid in expired:
                del self._jobs[jid]


_manager: JobManager | None = None


def get_job_manager(max_workers: int = 2, expiry_seconds: int = 3600) -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager(max_workers=max_workers, expiry_seconds=expiry_seconds)
    return _manager
