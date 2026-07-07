"""Property-based tests for lecture pipeline configuration wiring.

Covers project-hardening properties 5, 6 and 7:
- full merged configuration propagates to every sub-tool config,
- configured counts and summary length are applied by the pipeline,
- a supplied CLI flag overrides the configured value.

All external services (DatabaseBackend, transcriber, ingester, generators) are
mocked so nothing touches real infrastructure.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from hypothesis import given, settings
from hypothesis import strategies as st

from config import BaseConfig
from orchestrations.cli import orchestrate
from orchestrations.lecture_pipeline import LecturePipelineOrchestrator

SETTINGS = settings(max_examples=120, deadline=None)

LENGTHS = ["short", "medium", "long"]
DEVICES = ["cuda", "cpu"]
STRATEGIES = ["hybrid", "semantic", "keyword"]
FLASHCARD_FORMATS = ["anki", "quizlet", "plain"]


def _build_raw(
    *,
    whisper_model: str,
    whisper_device: str,
    rag_strategy: str,
    rag_prefix: str,
    summary_length: str,
    flashcard_count: int,
    flashcard_format: str,
    quiz_count: int,
    scratch_dir: str | None = None,
    pipeline_opts: dict | None = None,
) -> dict:
    """Build a full merged configuration document with populated sections."""
    raw: dict = {
        "llm": {"endpoint": "http://localhost:11434", "model": "test-model"},
        "embedding": {"backend": "ollama", "model": "embeddinggemma"},
        "database": {"backend": "chromadb", "mode": "persistent"},
        "paths": {},
        "video": {
            "whisper_model": whisper_model,
            "whisper_device": whisper_device,
        },
        "rag": {
            "strategy": rag_strategy,
            "collection_prefix": rag_prefix,
        },
        "summaries": {
            "summary_length": summary_length,
        },
        "flashcards": {
            "cards_per_topic": flashcard_count,
            "format": flashcard_format,
        },
        "quizzes": {
            "questions_per_topic": quiz_count,
        },
    }
    if scratch_dir is not None:
        raw["paths"]["scratch_dir"] = scratch_dir
    if pipeline_opts is not None:
        raw["orchestrations"] = {"lecture_pipeline": pipeline_opts}
    return raw


# Feature: project-hardening, Property 5: full merged configuration propagates to all sub-tool configs
@given(
    whisper_model=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz.-0123456789", min_size=1, max_size=20
    ),
    whisper_device=st.sampled_from(DEVICES),
    rag_strategy=st.sampled_from(STRATEGIES),
    rag_prefix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=12),
    summary_length=st.sampled_from(LENGTHS),
    flashcard_count=st.integers(min_value=1, max_value=50),
    flashcard_format=st.sampled_from(FLASHCARD_FORMATS),
    quiz_count=st.integers(min_value=1, max_value=50),
)
@SETTINGS
def test_merged_config_propagates_to_subtool_configs(
    whisper_model,
    whisper_device,
    rag_strategy,
    rag_prefix,
    summary_length,
    flashcard_count,
    flashcard_format,
    quiz_count,
):
    """Each sub-tool config field must equal the configured value, not defaults."""
    raw = _build_raw(
        whisper_model=whisper_model,
        whisper_device=whisper_device,
        rag_strategy=rag_strategy,
        rag_prefix=rag_prefix,
        summary_length=summary_length,
        flashcard_count=flashcard_count,
        flashcard_format=flashcard_format,
        quiz_count=quiz_count,
    )
    config = BaseConfig.from_dict(raw)
    db = MagicMock()

    orch = LecturePipelineOrchestrator(config, db)

    assert orch.video_config.whisper_model == whisper_model
    assert orch.video_config.whisper_device == whisper_device
    assert orch.rag_config.strategy == rag_strategy
    assert orch.rag_config.collection_prefix == rag_prefix
    assert orch.summary_config.summary_length == summary_length
    assert orch.flashcard_config.cards_per_topic == flashcard_count
    assert orch.flashcard_config.format == flashcard_format
    assert orch.quiz_config.questions_per_topic == quiz_count


# Feature: project-hardening, Property 6: configured counts and summary length are applied by the pipeline
@given(
    flashcard_count=st.integers(min_value=1, max_value=40),
    quiz_count=st.integers(min_value=1, max_value=40),
    summary_length=st.sampled_from(LENGTHS),
)
@SETTINGS
def test_configured_counts_and_length_applied(flashcard_count, quiz_count, summary_length):
    """Generators must receive configured counts; summary must use configured length."""
    scratch = tempfile.mkdtemp()
    raw = _build_raw(
        whisper_model="medium.en",
        whisper_device="cpu",
        rag_strategy="hybrid",
        rag_prefix="rag",
        summary_length=summary_length,
        flashcard_count=5,
        flashcard_format="anki",
        quiz_count=5,
        scratch_dir=scratch,
        pipeline_opts={
            "flashcard_count": flashcard_count,
            "quiz_count": quiz_count,
            "summary_length": summary_length,
        },
    )
    config = BaseConfig.from_dict(raw)
    db = MagicMock()

    mod = "orchestrations.lecture_pipeline"
    with (
        patch(f"{mod}.VideoTranscriber") as MockTranscriber,
        patch(f"{mod}.TranscriptCleaner") as MockCleaner,
        patch(f"{mod}.RAGIngester") as MockIngester,
        patch(f"{mod}.SummaryGenerator") as MockSummary,
        patch(f"{mod}.FlashcardGenerator") as MockFlashcard,
        patch(f"{mod}.QuizGenerator") as MockQuiz,
    ):
        MockTranscriber.return_value.transcribe_file.return_value = "raw transcript"
        MockCleaner.return_value.clean.return_value = "clean transcript"
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 3

        orch = LecturePipelineOrchestrator(config, db)
        orch.process_lecture(
            video_path=Path("lecture.mp4"),
            course="BIOL101",
            lecture_num=1,
        )

        # Counts are routed through the generators' `count` parameter.
        flash_kwargs = MockFlashcard.return_value.generate.call_args.kwargs
        quiz_kwargs = MockQuiz.return_value.generate.call_args.kwargs
        assert flash_kwargs["count"] == flashcard_count
        assert quiz_kwargs["count"] == quiz_count

        # Summary length is applied through the SummaryConfig handed to the generator.
        summary_cfg = MockSummary.call_args.args[0]
        assert summary_cfg.summary_length == summary_length


# Feature: project-hardening, Property 7: a supplied flag overrides the configured value
@given(
    config_count=st.integers(min_value=1, max_value=30),
    flag_count=st.integers(min_value=1, max_value=30),
)
@SETTINGS
def test_cli_flag_overrides_config(config_count, flag_count):
    """A supplied --flashcard-count flag overrides the configured count."""
    scratch = tempfile.mkdtemp()
    raw = _build_raw(
        whisper_model="medium.en",
        whisper_device="cpu",
        rag_strategy="hybrid",
        rag_prefix="rag",
        summary_length="medium",
        flashcard_count=5,
        flashcard_format="anki",
        quiz_count=5,
        scratch_dir=scratch,
        pipeline_opts={"flashcard_count": config_count},
    )
    config = BaseConfig.from_dict(raw)
    db = MagicMock()

    mod = "orchestrations.lecture_pipeline"
    runner = CliRunner()
    with (
        runner.isolated_filesystem(),
        patch("orchestrations.cli.load_cli_db", return_value=(config, db)),
        patch(f"{mod}.VideoTranscriber") as MockTranscriber,
        patch(f"{mod}.TranscriptCleaner") as MockCleaner,
        patch(f"{mod}.RAGIngester") as MockIngester,
        patch(f"{mod}.SummaryGenerator"),
        patch(f"{mod}.FlashcardGenerator") as MockFlashcard,
        patch(f"{mod}.QuizGenerator"),
    ):
        MockTranscriber.return_value.transcribe_file.return_value = "raw transcript"
        MockCleaner.return_value.clean.return_value = "clean transcript"
        MockIngester.return_value.ingest_path.return_value.chunks_indexed = 3

        Path("lecture.mp4").write_text("fake video")

        result = runner.invoke(
            orchestrate,
            [
                "lecture-pipeline",
                "lecture.mp4",
                "--course",
                "BIOL101",
                "--lecture",
                "1",
                "--flashcard-count",
                str(flag_count),
            ],
        )

        assert result.exit_code == 0, result.output
        flash_kwargs = MockFlashcard.return_value.generate.call_args.kwargs
        assert flash_kwargs["count"] == flag_count


def test_missing_required_inputs_yields_usage_error():
    """Omitting --course/--lecture must produce a Click usage error, not processing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("lecture.mp4").write_text("fake video")
        result = runner.invoke(orchestrate, ["lecture-pipeline", "lecture.mp4"])

    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_base_config_without_raw_falls_back():
    """A plain BaseConfig (empty raw) must still construct via to_dict() fallback."""
    config = BaseConfig()
    assert config.raw == {}
    orch = LecturePipelineOrchestrator(config, MagicMock())
    assert orch.video_config is not None
    assert orch.flashcard_config.cards_per_topic == 10
