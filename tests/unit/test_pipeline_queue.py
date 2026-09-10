"""Tests for the dependency-safe transcription queue (``pipeline_queue``).

No real Whisper or LLM models are used. Fake transcriber/cleaner doubles use
``time.sleep`` and record timestamped events so we can assert:

* The LLM clean of file A overlaps the Whisper transcribe of file B (they use
  different gate locks).
* Two Whisper transcribes never run at the same time (whisper exclusivity).
* A single failing file records an ``error`` while its siblings still succeed.
* ``skip_clean=True`` never calls the cleaner.

It also verifies the injection contract: real ``VideoTranscriber`` /
``TranscriptCleaner`` self-lock (``locks_internally = True``) so the queue does
not double-lock, while fake doubles (no marker) are gated by the queue itself.
"""

import threading
import time
from pathlib import Path

import pytest

from tools.video.pipeline_queue import (
    ModelGates,
    TranscriptJobResult,
    run_transcription_queue,
)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


class EventLog:
    """Thread-safe timestamped event recorder."""

    def __init__(self):
        self._lock = threading.Lock()
        self.events = []  # list of (label, phase, monotonic_time)

    def mark(self, label, phase):
        with self._lock:
            self.events.append((label, phase, time.monotonic()))

    def interval(self, label, action):
        """Return (start, end) for a given label/action pair."""
        start = next(
            t for (lbl, ph, t) in self.events if lbl == label and ph == f"{action}:start"
        )
        end = next(
            t for (lbl, ph, t) in self.events if lbl == label and ph == f"{action}:end"
        )
        return start, end


def _overlaps(a, b):
    """True if two (start, end) intervals overlap."""
    return a[0] < b[1] and b[0] < a[1]


class FakeTranscriber:
    """Fake transcriber. Does NOT self-lock, so the queue gates it."""

    def __init__(self, log, delay=0.05, fail_on=None, active=None):
        self.log = log
        self.delay = delay
        self.fail_on = fail_on or set()
        self.calls = []
        # Optional shared counter/event to detect concurrent whisper entry.
        self._active = active

    def transcribe_file(self, path):
        name = Path(path).stem
        self.calls.append(path)
        if name in self.fail_on:
            raise RuntimeError(f"boom:{name}")
        self.log.mark(name, "transcribe:start")
        if self._active is not None:
            self._active(name)
        time.sleep(self.delay)
        self.log.mark(name, "transcribe:end")
        return f"raw:{name}"


class FakeCleaner:
    """Fake cleaner. Does NOT self-lock, so the queue gates it."""

    def __init__(self, log, delay=0.05):
        self.log = log
        self.delay = delay
        self.calls = []

    def clean(self, raw):
        self.calls.append(raw)
        name = raw.split(":", 1)[1]
        self.log.mark(name, "clean:start")
        time.sleep(self.delay)
        self.log.mark(name, "clean:end")
        return f"clean:{name}"


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_clean_of_A_overlaps_transcribe_of_B():
    """Different locks: LLM clean(A) can run while Whisper transcribe(B) runs."""
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.15)
    cleaner = FakeCleaner(log, delay=0.15)

    files = [Path("A.mp4"), Path("B.mp4")]
    results = run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=cleaner,
        max_workers=2,
    )

    assert [r.source.stem for r in results] == ["A", "B"]
    assert all(r.error is None for r in results)
    assert all(r.raw is not None and r.cleaned is not None for r in results)

    clean_a = log.interval("A", "clean")
    transcribe_b = log.interval("B", "transcribe")
    assert _overlaps(clean_a, transcribe_b), (
        "clean(A) should overlap transcribe(B): "
        f"clean_a={clean_a}, transcribe_b={transcribe_b}"
    )


def test_whisper_is_exclusive():
    """Two transcribe calls must never be inside the whisper gate together."""
    log = EventLog()
    state = {"inside": 0, "max": 0}
    slock = threading.Lock()

    def on_active(_name):
        with slock:
            state["inside"] += 1
            state["max"] = max(state["max"], state["inside"])
        time.sleep(0.05)
        with slock:
            state["inside"] -= 1

    transcriber = FakeTranscriber(log, delay=0.0, active=on_active)

    files = [Path(f"F{i}.mp4") for i in range(4)]
    results = run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=None,
        skip_clean=True,
        max_workers=4,
    )

    assert all(r.error is None for r in results)
    assert state["max"] == 1, f"whisper not exclusive: max concurrent={state['max']}"


def test_two_transcribe_intervals_do_not_overlap():
    """Directly assert transcribe intervals are disjoint under many workers."""
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.1)

    files = [Path("A.mp4"), Path("B.mp4")]
    run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=None,
        skip_clean=True,
        max_workers=2,
    )

    a = log.interval("A", "transcribe")
    b = log.interval("B", "transcribe")
    assert not _overlaps(a, b), f"whisper transcribes overlapped: a={a}, b={b}"


def test_one_failure_does_not_drop_siblings():
    """Middle file raises; the other two succeed and all results returned."""
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.01, fail_on={"B"})
    cleaner = FakeCleaner(log, delay=0.01)

    files = [Path("A.mp4"), Path("B.mp4"), Path("C.mp4")]
    results = run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=cleaner,
        max_workers=2,
    )

    assert len(results) == 3
    by_name = {r.source.stem: r for r in results}

    assert by_name["A"].error is None
    assert by_name["A"].raw == "raw:A"
    assert by_name["A"].cleaned == "clean:A"

    assert by_name["C"].error is None
    assert by_name["C"].raw == "raw:C"
    assert by_name["C"].cleaned == "clean:C"

    assert by_name["B"].error == "boom:B"
    assert by_name["B"].raw is None
    assert by_name["B"].cleaned is None


def test_skip_clean_never_calls_cleaner():
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.0)
    cleaner = FakeCleaner(log, delay=0.0)

    files = [Path("A.mp4"), Path("B.mp4")]
    results = run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=cleaner,
        skip_clean=True,
        max_workers=2,
    )

    assert cleaner.calls == []
    assert all(r.cleaned is None for r in results)
    assert all(r.raw is not None for r in results)


def test_no_cleaner_leaves_cleaned_none():
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.0)

    results = run_transcription_queue(
        [Path("A.mp4")],
        transcriber=transcriber,
        cleaner=None,
        max_workers=1,
    )
    assert results[0].cleaned is None
    assert results[0].raw == "raw:A"


def test_max_workers_one_is_valid_and_serial():
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.05)

    files = [Path("A.mp4"), Path("B.mp4")]
    results = run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=None,
        skip_clean=True,
        max_workers=1,
    )
    assert [r.source.stem for r in results] == ["A", "B"]
    a = log.interval("A", "transcribe")
    b = log.interval("B", "transcribe")
    assert not _overlaps(a, b)


def test_empty_files_returns_empty():
    transcriber = FakeTranscriber(EventLog())
    assert run_transcription_queue([], transcriber=transcriber) == []


def test_result_records_parent():
    log = EventLog()
    transcriber = FakeTranscriber(log, delay=0.0)
    results = run_transcription_queue(
        [Path("course/P1L1/a.mp4")],
        transcriber=transcriber,
        skip_clean=True,
        max_workers=1,
    )
    assert results[0].parent == Path("course/P1L1")
    assert isinstance(results[0], TranscriptJobResult)


# --------------------------------------------------------------------------- #
# Injection contract: real components self-lock; queue must not double-lock.
# --------------------------------------------------------------------------- #


class SelfLockingTranscriber:
    """Mimics the real VideoTranscriber: self-locks with gates.whisper."""

    locks_internally = True

    def __init__(self, gates, log):
        self._gates = gates
        self.log = log

    def transcribe_file(self, path):
        name = Path(path).stem
        with self._gates.whisper:
            self.log.mark(name, "transcribe:start")
            time.sleep(0.05)
            self.log.mark(name, "transcribe:end")
        return f"raw:{name}"


def test_self_locking_transcriber_not_double_locked():
    """A self-locking transcriber sharing the queue's gates must not deadlock.

    If the queue also took gates.whisper (a non-reentrant Lock), acquiring it
    twice in the same thread would deadlock. Completion proves the queue
    respected ``locks_internally`` and did not double-lock.
    """
    gates = ModelGates()
    log = EventLog()
    transcriber = SelfLockingTranscriber(gates, log)

    files = [Path("A.mp4"), Path("B.mp4")]
    results = run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=None,
        skip_clean=True,
        max_workers=2,
        gates=gates,
    )

    assert [r.source.stem for r in results] == ["A", "B"]
    assert all(r.error is None for r in results)
    # Even self-locked, whisper stays exclusive.
    a = log.interval("A", "transcribe")
    b = log.interval("B", "transcribe")
    assert not _overlaps(a, b)


def test_real_components_advertise_locks_internally():
    from tools.video.clean import TranscriptCleaner
    from tools.video.transcribe import VideoTranscriber

    assert getattr(VideoTranscriber, "locks_internally", False) is True
    assert getattr(TranscriptCleaner, "locks_internally", False) is True


def test_model_gates_locks_are_independent():
    gates = ModelGates()
    assert gates.whisper is not gates.llm
    with gates.whisper:
        # llm lock is still acquirable while whisper is held
        acquired = gates.llm.acquire(blocking=False)
        assert acquired
        gates.llm.release()
