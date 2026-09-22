"""Dependency-safe transcription queue with model mutexes.

Whisper workers only transcribe. As soon as a file's transcript is ready it
is pushed to a dedicated LLM worker, so Gemma can clean lecture 1 while
Whisper is already on lecture 2. Whisper is exclusive; the LLM is exclusive;
audio extract stays ungated.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

MAX_WORKERS = 8

ProgressFn = Callable[[str, int, int, Path], None]


def clamp_workers(n: object) -> int:
    """Clamp a worker count to ``[1, MAX_WORKERS]``."""
    try:
        value = int(n)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = 1
    return max(1, min(value, MAX_WORKERS))


class ModelGates:
    """Process-local mutexes for the two shared, single-instance models.

    Exposes two :class:`threading.Lock` objects, ``whisper`` and ``llm``,
    each usable directly as a context manager::

        with gates.whisper:
            model.transcribe(...)

        with gates.llm:
            backend.complete(...)

    Both locks are independent, so a Whisper call and an LLM call can run
    at the same time, but two Whisper calls (or two LLM calls) cannot.
    """

    def __init__(self) -> None:
        self.whisper: threading.Lock = threading.Lock()
        self.llm: threading.Lock = threading.Lock()


_DEFAULT_GATES = ModelGates()


def default_gates() -> ModelGates:
    """Return the shared process-local :class:`ModelGates` singleton."""
    return _DEFAULT_GATES


@dataclass
class TranscriptJobResult:
    """Result of transcribing (and optionally cleaning) a single file."""

    source: Path
    parent: Path
    raw: str | None = None
    cleaned: str | None = None
    error: str | None = None


@runtime_checkable
class _SelfLocking(Protocol):
    locks_internally: bool


def _locks_internally(component: object) -> bool:
    return bool(getattr(component, "locks_internally", False))


def _emit(on_progress: ProgressFn | None, stage: str, index: int, total: int, path: Path) -> None:
    if on_progress is None:
        return
    try:
        on_progress(stage, index, total, path)
    except Exception:
        return


def _join_interruptible(threads: list[threading.Thread]) -> None:
    """Join workers in short slices so Ctrl+C can reach the main thread.

    A blocking ``Thread.join()`` (or ``ThreadPoolExecutor.shutdown(wait=True)``)
    swallows SIGINT until the current Whisper/Ollama call in a worker returns.
    Waking every 200ms lets KeyboardInterrupt abort the pipeline.
    """
    remaining = list(threads)
    while remaining:
        remaining = [thread for thread in remaining if thread.is_alive()]
        for thread in remaining:
            thread.join(timeout=0.2)


def run_transcription_queue(
    files,
    *,
    transcriber,
    cleaner=None,
    skip_clean: bool = False,
    max_workers: int = 2,
    gates: ModelGates | None = None,
    on_progress: ProgressFn | None = None,
) -> list[TranscriptJobResult]:
    """Transcribe files, then clean each one as soon as Whisper finishes.

    Whisper workers never wait on the LLM. They push ``(index, path, raw)``
    onto a clean queue and pick up the next file. A single LLM worker drains
    that queue, so cleaning of file *n* overlaps transcription of file *n+1*.
    """
    if gates is None:
        gates = default_gates()

    file_list = [Path(f) for f in files]
    total = len(file_list)
    if total == 0:
        return []

    max_workers = clamp_workers(max_workers)
    transcriber_self_locks = _locks_internally(transcriber)
    cleaner_self_locks = _locks_internally(cleaner) if cleaner is not None else False
    do_clean = bool(cleaner is not None and not skip_clean)

    results: list[TranscriptJobResult] = [
        TranscriptJobResult(source=path, parent=path.parent) for path in file_list
    ]
    stop = threading.Event()
    whisper_q: queue.Queue[tuple[int, Path] | None] = queue.Queue()
    clean_q: queue.Queue[tuple[int, Path, str] | None] = queue.Queue()

    for index, path in enumerate(file_list):
        whisper_q.put((index, path))
    for _ in range(max_workers):
        whisper_q.put(None)

    def _transcribe(path: Path) -> str:
        if transcriber_self_locks:
            return transcriber.transcribe_file(path)
        with gates.whisper:
            return transcriber.transcribe_file(path)

    def _clean_text(raw: str) -> str:
        if cleaner_self_locks:
            return cleaner.clean(raw)
        with gates.llm:
            return cleaner.clean(raw)

    def whisper_worker() -> None:
        while not stop.is_set():
            try:
                item = whisper_q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if item is None or stop.is_set():
                    return
                index, path = item
                _emit(on_progress, "whisper", index, total, path)
                try:
                    raw = _transcribe(path)
                except Exception as exc:  # noqa: BLE001
                    results[index].error = str(exc)
                    _emit(on_progress, "error", index, total, path)
                    continue
                if stop.is_set():
                    return
                results[index].raw = raw
                if do_clean:
                    clean_q.put((index, path, raw))
                else:
                    _emit(on_progress, "done", index, total, path)
            finally:
                whisper_q.task_done()

    def llm_worker() -> None:
        while not stop.is_set():
            try:
                item = clean_q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if item is None or stop.is_set():
                    return
                index, path, raw = item
                _emit(on_progress, "clean", index, total, path)
                try:
                    results[index].cleaned = _clean_text(raw)
                except Exception as exc:  # noqa: BLE001
                    results[index].error = str(exc)
                    _emit(on_progress, "error", index, total, path)
                    continue
                _emit(on_progress, "done", index, total, path)
            finally:
                clean_q.task_done()

    whisper_threads = [
        threading.Thread(target=whisper_worker, name=f"whisper-{i}", daemon=True)
        for i in range(max_workers)
    ]
    for thread in whisper_threads:
        thread.start()

    llm_thread = None
    if do_clean:
        llm_thread = threading.Thread(target=llm_worker, name="llm-clean", daemon=True)
        llm_thread.start()

    try:
        _join_interruptible(whisper_threads)
        if llm_thread is not None:
            clean_q.put(None)
            _join_interruptible([llm_thread])
    except KeyboardInterrupt:
        stop.set()
        for _ in range(max_workers):
            whisper_q.put(None)
        clean_q.put(None)
        raise

    return results
