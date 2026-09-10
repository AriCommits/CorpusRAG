"""Tests for orchestrations."""

from unittest.mock import MagicMock, patch

import pytest

from config import BaseConfig, DatabaseConfig
from db import ChromaDBBackend
from orchestrations import LecturePipelineOrchestrator


@pytest.fixture
def base_config(tmp_path):
    """Create a test configuration."""
    return BaseConfig(
        database=DatabaseConfig(
            mode="persistent",
            persist_directory=tmp_path / "chroma",
        )
    )


@pytest.fixture
def db_backend(base_config):
    """Create a test database backend."""
    return ChromaDBBackend(base_config.database)


def test_lecture_pipeline_orchestrator_creation(base_config, db_backend):
    """Test creating a lecture pipeline orchestrator."""
    orchestrator = LecturePipelineOrchestrator(base_config, db_backend)

    assert orchestrator is not None
    assert orchestrator.config == base_config
    assert orchestrator.db == db_backend


def test_lecture_pipeline_format(base_config, db_backend):
    """Test formatting lecture materials."""
    orchestrator = LecturePipelineOrchestrator(base_config, db_backend)

    result = {
        "course": "CS101",
        "lecture_num": 1,
        "collection": "CS101_Lecture01",
        "transcript": "This is a transcript",
        "chunks_indexed": 10,
        "summary": "This is a summary",
        "flashcards": "Q: Question?\nA: Answer",
        "quiz": "1. Test question?",
    }

    formatted = orchestrator.format_lecture_materials(result)

    assert "CS101 - Lecture 1" in formatted
    assert "This is a transcript" in formatted
    assert "This is a summary" in formatted


# ---------------------------------------------------------------------------
# process_course: shared-queue refactor (Sprint 2 C4)
# ---------------------------------------------------------------------------

MOD = "orchestrations.lecture_pipeline"


def _course_config(tmp_path):
    """Build a BaseConfig with a real scratch dir for temp transcript writes."""
    return BaseConfig.from_dict(
        {
            "llm": {"endpoint": "http://localhost:11434", "model": "test-model"},
            "embedding": {"backend": "ollama", "model": "embeddinggemma"},
            "database": {"backend": "chromadb", "mode": "persistent"},
            "paths": {"scratch_dir": str(tmp_path / "scratch")},
            "video": {"whisper_model": "medium.en", "whisper_device": "cpu"},
            "rag": {"strategy": "hybrid", "collection_prefix": "rag"},
            "summaries": {"summary_length": "medium"},
            "flashcards": {"cards_per_topic": 5, "format": "anki"},
            "quizzes": {"questions_per_topic": 5},
        }
    )


class _FakeJob:
    """Stand-in for TranscriptJobResult with the attributes C4 relies on."""

    def __init__(self, source, raw="raw", cleaned="cleaned", error=None):
        self.source = source
        self.parent = source.parent
        self.raw = raw
        self.cleaned = cleaned
        self.error = error


def test_process_course_discovers_nested_and_queues(tmp_path):
    """Nested tmp tree yields two transcribe jobs via the shared queue."""
    config = _course_config(tmp_path)
    db = MagicMock()

    # Build a nested tree; discovery is mocked, so files need not be real,
    # but we create them so the sorted source order is deterministic.
    root = tmp_path / "course"
    (root / "P1L1").mkdir(parents=True)
    (root / "P1L2").mkdir(parents=True)
    a = root / "P1L1" / "a.mp4"
    b = root / "P1L2" / "b.mp4"
    a.write_text("x")
    b.write_text("x")

    with (
        patch(f"{MOD}.discover_media_files", return_value=[a, b]) as MockDiscover,
        patch(f"{MOD}.run_transcription_queue") as MockQueue,
        patch(f"{MOD}.VideoTranscriber") as MockTranscriber,
        patch(f"{MOD}.TranscriptCleaner") as MockCleaner,
        patch(f"{MOD}.ModelGates") as MockGates,
        patch(f"{MOD}.RAGIngester") as MockIngester,
        patch(f"{MOD}.SummaryGenerator"),
        patch(f"{MOD}.FlashcardGenerator"),
        patch(f"{MOD}.QuizGenerator"),
    ):
        MockQueue.return_value = [_FakeJob(a), _FakeJob(b)]
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 3

        orch = LecturePipelineOrchestrator(config, db)
        results = orch.process_course(root, course="BIOL101")

    # Discovery uses the config extensions and recursive=True.
    MockDiscover.assert_called_once()
    disc_args, disc_kwargs = MockDiscover.call_args
    assert disc_args[0] == root
    assert disc_args[1] == orch.video_config.supported_extensions
    assert disc_kwargs["recursive"] is True

    # Queue receives the discovered files and one shared transcriber/cleaner/gates.
    MockQueue.assert_called_once()
    q_args, q_kwargs = MockQueue.call_args
    assert q_args[0] == [a, b]
    assert q_kwargs["transcriber"] is MockTranscriber.return_value
    assert q_kwargs["cleaner"] is MockCleaner.return_value
    assert q_kwargs["gates"] is MockGates.return_value
    # Exactly one Whisper load and one cleaner for the whole course.
    MockTranscriber.assert_called_once()
    MockCleaner.assert_called_once()
    MockGates.assert_called_once()

    # Two successful jobs -> two results with sequential lecture numbers.
    assert len(results) == 2
    assert [r["lecture_num"] for r in results] == [1, 2]
    assert results[0]["collection"] == "BIOL101_Lecture01"
    assert results[1]["collection"] == "BIOL101_Lecture02"


def test_process_course_generators_run_after_queue(tmp_path):
    """Generators must not be constructed before the queue has drained."""
    config = _course_config(tmp_path)
    db = MagicMock()
    root = tmp_path / "course"
    root.mkdir()
    a = root / "a.mp4"
    a.write_text("x")

    call_order = []

    def _queue(*_args, **_kwargs):
        call_order.append("queue")
        return [_FakeJob(a)]

    with (
        patch(f"{MOD}.discover_media_files", return_value=[a]),
        patch(f"{MOD}.run_transcription_queue", side_effect=_queue),
        patch(f"{MOD}.VideoTranscriber"),
        patch(f"{MOD}.TranscriptCleaner"),
        patch(f"{MOD}.ModelGates"),
        patch(f"{MOD}.RAGIngester") as MockIngester,
        patch(f"{MOD}.SummaryGenerator") as MockSummary,
        patch(f"{MOD}.FlashcardGenerator") as MockFlashcard,
        patch(f"{MOD}.QuizGenerator") as MockQuiz,
    ):
        def _record(name):
            def _factory(*_a, **_k):
                call_order.append(name)
                return MagicMock()

            return _factory

        MockIngester.side_effect = _record("ingest")
        MockSummary.side_effect = _record("summary")
        MockFlashcard.side_effect = _record("flashcards")
        MockQuiz.side_effect = _record("quiz")
        # ingest_path must still return a chunks_indexed value.
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 1

        orch = LecturePipelineOrchestrator(config, db)
        orch.process_course(root, course="CS101")

    # The queue must be the first heavy step; every generator comes after it.
    assert call_order[0] == "queue"
    for step in ("ingest", "summary", "flashcards", "quiz"):
        assert step in call_order
        assert call_order.index(step) > call_order.index("queue")


def test_process_course_needs_both_discovery_outputs(tmp_path):
    """Every discovered+successful file must reach the queue and produce a result."""
    config = _course_config(tmp_path)
    db = MagicMock()
    root = tmp_path / "course"
    (root / "P1L1").mkdir(parents=True)
    (root / "P1L2").mkdir(parents=True)
    a = root / "P1L1" / "a.mp4"
    b = root / "P1L2" / "b.mp4"
    a.write_text("x")
    b.write_text("x")

    with (
        patch(f"{MOD}.discover_media_files", return_value=[a, b]),
        patch(f"{MOD}.run_transcription_queue") as MockQueue,
        patch(f"{MOD}.VideoTranscriber"),
        patch(f"{MOD}.TranscriptCleaner"),
        patch(f"{MOD}.ModelGates"),
        patch(f"{MOD}.RAGIngester") as MockIngester,
        patch(f"{MOD}.SummaryGenerator"),
        patch(f"{MOD}.FlashcardGenerator"),
        patch(f"{MOD}.QuizGenerator"),
    ):
        MockQueue.return_value = [_FakeJob(a), _FakeJob(b)]
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 2

        orch = LecturePipelineOrchestrator(config, db)
        results = orch.process_course(root, course="BIOL101")

    # Both discovery outputs flow into the single queue call.
    assert MockQueue.call_args.args[0] == [a, b]
    assert len(results) == 2


def test_process_course_skips_failed_jobs_and_numbers_by_sorted_source(tmp_path):
    """Failures are dropped; lecture numbers follow sorted successful source order."""
    config = _course_config(tmp_path)
    db = MagicMock()
    root = tmp_path / "course"
    root.mkdir()
    a = root / "a.mp4"
    b = root / "b.mp4"
    c = root / "c.mp4"
    for f in (a, b, c):
        f.write_text("x")

    with (
        patch(f"{MOD}.discover_media_files", return_value=[a, b, c]),
        patch(f"{MOD}.run_transcription_queue") as MockQueue,
        patch(f"{MOD}.VideoTranscriber"),
        patch(f"{MOD}.TranscriptCleaner"),
        patch(f"{MOD}.ModelGates"),
        patch(f"{MOD}.RAGIngester") as MockIngester,
        patch(f"{MOD}.SummaryGenerator"),
        patch(f"{MOD}.FlashcardGenerator"),
        patch(f"{MOD}.QuizGenerator"),
    ):
        # Return out of order with a middle failure to prove sorting + skip.
        MockQueue.return_value = [
            _FakeJob(c, raw="rc", cleaned="cc"),
            _FakeJob(b, raw=None, cleaned=None, error="boom"),
            _FakeJob(a, raw="ra", cleaned="ca"),
        ]
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 1

        orch = LecturePipelineOrchestrator(config, db)
        results = orch.process_course(root, course="BIOL101")

    # Only a and c succeeded; numbered 1,2 by sorted source (a before c).
    assert len(results) == 2
    assert results[0]["lecture_num"] == 1
    assert results[1]["lecture_num"] == 2
    assert results[0]["transcript"] == "ca"
    assert results[1]["transcript"] == "cc"


def test_process_course_skip_clean_omits_cleaner(tmp_path):
    """skip_clean=True passes no cleaner and uses raw transcript text."""
    config = _course_config(tmp_path)
    db = MagicMock()
    root = tmp_path / "course"
    root.mkdir()
    a = root / "a.mp4"
    a.write_text("x")

    with (
        patch(f"{MOD}.discover_media_files", return_value=[a]),
        patch(f"{MOD}.run_transcription_queue") as MockQueue,
        patch(f"{MOD}.VideoTranscriber"),
        patch(f"{MOD}.TranscriptCleaner") as MockCleaner,
        patch(f"{MOD}.ModelGates"),
        patch(f"{MOD}.RAGIngester") as MockIngester,
        patch(f"{MOD}.SummaryGenerator"),
        patch(f"{MOD}.FlashcardGenerator"),
        patch(f"{MOD}.QuizGenerator"),
    ):
        MockQueue.return_value = [_FakeJob(a, raw="ra", cleaned=None)]
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 1

        orch = LecturePipelineOrchestrator(config, db)
        results = orch.process_course(root, course="BIOL101", skip_clean=True)

    # No cleaner constructed; queue told to skip cleaning.
    MockCleaner.assert_not_called()
    q_kwargs = MockQueue.call_args.kwargs
    assert q_kwargs["cleaner"] is None
    assert q_kwargs["skip_clean"] is True
    # Raw transcript is used when cleaning is skipped.
    assert results[0]["transcript"] == "ra"
