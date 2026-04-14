"""Tests for orchestrations."""


import pytest

from config import BaseConfig, DatabaseConfig
from db import ChromaDBBackend
from orchestrations import (
    KnowledgeBaseOrchestrator,
    LecturePipelineOrchestrator,
    StudySessionOrchestrator,
)


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


def test_study_session_orchestrator_creation(base_config, db_backend):
    """Test creating a study session orchestrator."""
    orchestrator = StudySessionOrchestrator(base_config, db_backend)

    assert orchestrator is not None
    assert orchestrator.config == base_config
    assert orchestrator.db == db_backend


def test_study_session_format(base_config, db_backend):
    """Test formatting a study session."""
    orchestrator = StudySessionOrchestrator(base_config, db_backend)

    session = {
        "collection": "test_collection",
        "topic": "Test Topic",
        "summary": "This is a summary",
        "flashcards": "Q: Question?\nA: Answer",
        "quiz": "1. Test question?",
    }

    formatted = orchestrator.format_session(session)

    assert "test_collection" in formatted
    assert "Test Topic" in formatted
    assert "This is a summary" in formatted
    assert "Q: Question?" in formatted


def test_knowledge_base_orchestrator_creation(base_config, db_backend):
    """Test creating a knowledge base orchestrator."""
    orchestrator = KnowledgeBaseOrchestrator(base_config, db_backend)

    assert orchestrator is not None
    assert orchestrator.config == base_config
    assert orchestrator.db == db_backend


def test_knowledge_base_list_collections(base_config, db_backend):
    """Test listing collections."""
    orchestrator = KnowledgeBaseOrchestrator(base_config, db_backend)

    # Initially should be empty or have test collections
    collections = orchestrator.list_collections()

    assert isinstance(collections, list)


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
