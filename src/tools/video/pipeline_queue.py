"""Dependency-safe transcription queue with model mutexes.

This module provides a small boss-worker style queue that runs
transcription (Whisper) and cleaning (LLM) across multiple files
concurrently while guaranteeing that:

* Only **one** Whisper transcription runs at a time (``gates.whisper``).
* Only **one** LLM cleaning runs at a time (``gates.llm``).
* Whisper of one file and LLM cleaning of another file **may overlap**
  because they take different locks.
* Audio extraction (ffmpeg) is never gated, so it overlaps Whisper.

The queue shares a single ``VideoTranscriber`` and a single
``TranscriptCleaner`` across all workers so the Whisper weights are loaded
once. Per-file failures are isolated: a raising file records an ``error``
and its siblings still run and are returned.

Discovery is intentionally *not* part of this module — the caller passes an
explicit list of files (see ``discover_media_files``).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

MAX_WORKERS = 8


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


# A single process-local default so that independently constructed
# transcribers/cleaners still serialize against the same models when the
# caller does not pass an explicit ``ModelGates``.
_DEFAULT_GATES = ModelGates()


def default_gates() -> ModelGates:
    """Return the shared process-local :class:`ModelGates` singleton."""
    return _DEFAULT_GATES


@dataclass
class TranscriptJobResult:
    """Result of transcribing (and optionally cleaning) a single file.

    Attributes:
        source: The input media file.
        parent: ``source.parent`` — used by callers to group per folder.
        raw: Raw transcript text, or ``None`` if transcription failed.
        cleaned: Cleaned transcript text, or ``None`` if cleaning was
            skipped or failed.
        error: ``str(exception)`` if the job failed, otherwise ``None``.
    """

    source: Path
    parent: Path
    raw: str | None = None
    cleaned: str | None = None
    error: str | None = None


@runtime_checkable
class _SelfLocking(Protocol):
    """Components that already take the appropriate gate lock internally.

    A ``VideoTranscriber`` / ``TranscriptCleaner`` that has been given a
    ``ModelGates`` locks the model call itself. The queue must not wrap that
    call in the same lock again (that would deadlock a non-reentrant Lock or
    at best redundantly serialize). Such components advertise this by setting
    ``locks_internally = True``. Fake test doubles that do *not* self-lock
    leave it falsey (the default), so the queue applies the gate for them.
    """

    locks_internally: bool


def _locks_internally(component: object) -> bool:
    return bool(getattr(component, "locks_internally", False))


def run_transcription_queue(
    files,
    *,
    transcriber,
    cleaner=None,
    skip_clean: bool = False,
    max_workers: int = 2,
    gates: ModelGates | None = None,
) -> list[TranscriptJobResult]:
    """Transcribe (and optionally clean) many files concurrently.

    Args:
        files: Iterable of media file paths. One job per file.
        transcriber: Shared object with ``transcribe_file(path) -> str``.
        cleaner: Optional shared object with ``clean(text) -> str``.
        skip_clean: If ``True``, never call ``cleaner``.
        max_workers: Thread pool size. Clamped to ``[1, MAX_WORKERS]``.
            ``1`` is fully serial.
        gates: Optional :class:`ModelGates`. Defaults to the process-local
            singleton so independent components still serialize correctly.

    Returns:
        A ``TranscriptJobResult`` per input file, in input order. Failures
        are recorded via ``error`` and never abort sibling jobs. This
        function never raises for a per-file failure; the caller (CLI)
        decides the exit code.
    """
    if gates is None:
        gates = default_gates()

    file_list = [Path(f) for f in files]
    max_workers = clamp_workers(max_workers)

    # Whether the queue itself should take the gate lock. If the component
    # self-locks (real VideoTranscriber/TranscriptCleaner with gates), we must
    # not lock again. Test fakes do not self-lock, so the queue gates them.
    transcriber_self_locks = _locks_internally(transcriber)
    cleaner_self_locks = _locks_internally(cleaner) if cleaner is not None else False

    def _process(path: Path) -> TranscriptJobResult:
        result = TranscriptJobResult(source=path, parent=path.parent)
        try:
            if transcriber_self_locks:
                raw = transcriber.transcribe_file(path)
            else:
                with gates.whisper:
                    raw = transcriber.transcribe_file(path)
            result.raw = raw

            if not skip_clean and cleaner is not None:
                if cleaner_self_locks:
                    result.cleaned = cleaner.clean(raw)
                else:
                    with gates.llm:
                        result.cleaned = cleaner.clean(raw)
        except Exception as exc:  # noqa: BLE001 - isolate per-file failures
            result.error = str(exc)
        return result

    if not file_list:
        return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # executor.map preserves input order and shares one transcriber/cleaner.
        return list(executor.map(_process, file_list))
