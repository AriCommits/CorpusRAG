"""Integration tests for flashcard, summary, and quiz generators."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.base import DatabaseConfig, LLMConfig
from db import ChromaDBBackend
from tools.flashcards import FlashcardConfig, FlashcardGenerator
from tools.quizzes import QuizConfig, QuizGenerator
from tools.rag import RAGConfig, RAGIngester
from tools.summaries import SummaryConfig, SummaryGenerator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def db_config(temp_dir: Path) -> DatabaseConfig:
    """Create test database configuration."""
    return DatabaseConfig(
        backend="chromadb",
        mode="persistent",
        persist_directory=temp_dir / "chroma_db",
    )


@pytest.fixture
def db_backend(db_config: DatabaseConfig) -> ChromaDBBackend:
    """Create test database backend."""
    return ChromaDBBackend(db_config)


@pytest.fixture
def llm_config() -> LLMConfig:
    """Create test LLM configuration."""
    return LLMConfig(
        backend="ollama",
        endpoint="http://localhost:11434",
        model="gemma4:26b-a4b-it-q4_K_M",
    )


@pytest.fixture
def flashcard_config(db_config: DatabaseConfig, llm_config: LLMConfig) -> FlashcardConfig:
    """Create test flashcard configuration."""
    return FlashcardConfig(
        database=db_config,
        llm=llm_config,
        cards_per_topic=5,
        format="plain",
    )


@pytest.fixture
def summary_config(db_config: DatabaseConfig, llm_config: LLMConfig) -> SummaryConfig:
    """Create test summary configuration."""
    return SummaryConfig(
        database=db_config,
        llm=llm_config,
        summary_length="medium",
        include_keywords=True,
        include_outline=True,
    )


@pytest.fixture
def quiz_config(db_config: DatabaseConfig, llm_config: LLMConfig) -> QuizConfig:
    """Create test quiz configuration."""
    return QuizConfig(
        database=db_config,
        llm=llm_config,
        questions_per_topic=5,
        question_types=["multiple_choice", "true_false", "short_answer"],
        include_explanations=True,
        format="markdown",
    )


@pytest.fixture
def populated_collection(
    db_config: DatabaseConfig, db_backend: ChromaDBBackend, temp_dir: Path
) -> Generator[str, None, None]:
    """Create and populate a test collection with sample documents."""
    # Create sample markdown documents
    sample_docs = {
        "doc1.md": """# Machine Learning Basics

## Introduction to ML
Machine learning is a subset of artificial intelligence that enables systems to learn and improve
from experience without being explicitly programmed.

## Types of Machine Learning

### Supervised Learning
Supervised learning requires labeled training data. The algorithm learns to map inputs to outputs.
Examples include classification and regression tasks.

### Unsupervised Learning
Unsupervised learning works with unlabeled data. Algorithms identify patterns and structure.
Clustering and dimensionality reduction are common techniques.

## Key Concepts
- Features: Input variables used for prediction
- Labels: Target output values in supervised learning
- Model: The learned representation of patterns in data
- Training: Process of fitting the model to data

Tags:
- #machine-learning #supervised-learning
""",
        "doc2.md": """# Python Programming Guide

## Getting Started with Python
Python is a high-level, interpreted programming language known for its simplicity and readability.

## Core Concepts

### Variables and Data Types
Python supports dynamic typing. Common types include int, float, str, list, dict, and tuple.

### Functions
Functions are reusable blocks of code. They accept parameters and return values.

### Object-Oriented Programming
Python supports OOP with classes, inheritance, and polymorphism.

## Best Practices
- Use meaningful variable names
- Write modular, reusable code
- Follow PEP 8 style guide
- Use type hints for clarity

Tags:
- #python #programming
""",
        "doc3.md": """# Data Science Fundamentals

## What is Data Science?
Data science combines statistics, programming, and domain knowledge to extract insights from data.

## Data Processing Steps

### Data Collection
Gathering raw data from various sources such as databases, APIs, or sensors.

### Data Cleaning
Removing duplicates, handling missing values, and correcting inconsistencies.

### Exploratory Data Analysis
Understanding data through visualization and statistical analysis.

### Feature Engineering
Creating and selecting relevant features for modeling.

## Tools and Libraries
Popular Python libraries include pandas, numpy, scikit-learn, and matplotlib.

Tags:
- #data-science #statistics
""",
    }

    # Write sample documents to temp directory
    docs_dir = temp_dir / "documents"
    docs_dir.mkdir(exist_ok=True)
    for filename, content in sample_docs.items():
        (docs_dir / filename).write_text(content)

    # Create RAG config for ingestion
    from config.base import EmbeddingConfig, PathsConfig
    from tools.rag.config import ParentStoreConfig

    rag_config = RAGConfig(
        llm=LLMConfig(
            backend="ollama",
            endpoint="http://localhost:11434",
            model="gemma4:26b-a4b-it-q4_K_M",
        ),
        embedding=EmbeddingConfig(
            backend="ollama",
            model="embeddinggemma",
        ),
        database=db_config,
        paths=PathsConfig(
            vault=temp_dir / "vault",
            scratch_dir=temp_dir / "scratch",
            output_dir=temp_dir / "output",
        ),
        parent_store=ParentStoreConfig(
            type="local_file",
            path=temp_dir / "parent_store",
        ),
    )

    # Mock embedding client and ingest documents
    with patch("tools.rag.ingest.EmbeddingClient") as mock_embedder_class:
        mock_embedder = MagicMock()
        mock_embedder_class.return_value = mock_embedder

        def mock_embed(texts):
            return [[0.1] * 384 for _ in texts]

        mock_embedder.embed_texts = mock_embed

        ingester = RAGIngester(rag_config, db_backend)
        ingester.ingest_path(docs_dir, "test_collection")

    yield "test_collection"


class TestFlashcardGenerator:
    """Test flashcard generator with real document data."""

    def test_generate_from_real_documents(
        self, flashcard_config: FlashcardConfig, db_backend: ChromaDBBackend,
        populated_collection: str
    ) -> None:
        """Test generating flashcards from real ingested documents."""
        generator = FlashcardGenerator(flashcard_config, db_backend)

        with patch("tools.rag.embeddings.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.embed_query.return_value = [0.1] * 384

            flashcards = generator.generate(populated_collection, difficulty="intermediate", count=3)

            # Verify flashcards were generated
            assert len(flashcards) > 0
            assert len(flashcards) <= 3

            # Verify structure
            for card in flashcards:
                assert "front" in card
                assert "back" in card
                assert "difficulty" in card
                assert card["difficulty"] == "intermediate"
                assert "collection" in card
                assert card["collection"] == populated_collection

    def test_empty_collection_raises_valueerror(
        self, flashcard_config: FlashcardConfig, db_backend: ChromaDBBackend
    ) -> None:
        """Test that empty collection raises ValueError."""
        generator = FlashcardGenerator(flashcard_config, db_backend)

        # Create an empty collection
        full_collection = f"{flashcard_config.collection_prefix}_empty_collection"
        db_backend.add_collection(full_collection)

        with patch("tools.rag.embeddings.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.embed_query.return_value = [0.1] * 384

            with pytest.raises(ValueError, match="No documents found"):
                generator.generate("empty_collection")

    def test_nonexistent_collection_raises_valueerror(
        self, flashcard_config: FlashcardConfig, db_backend: ChromaDBBackend
    ) -> None:
        """Test that nonexistent collection raises ValueError."""
        generator = FlashcardGenerator(flashcard_config, db_backend)

        with pytest.raises(ValueError, match="does not exist"):
            generator.generate("nonexistent_collection")


class TestSummaryGenerator:
    """Test summary generator with real document data."""

    def test_generate_from_real_documents(
        self, summary_config: SummaryConfig, db_backend: ChromaDBBackend,
        populated_collection: str
    ) -> None:
        """Test generating summary from real ingested documents."""
        generator = SummaryGenerator(summary_config, db_backend)

        with patch("tools.rag.embeddings.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.embed_query.return_value = [0.1] * 384

            summary = generator.generate(populated_collection, topic=None)

            # Verify summary structure
            assert "summary" in summary
            assert "collection" in summary
            assert summary["collection"] == populated_collection
            assert len(summary["summary"]) > 0

            # Verify optional fields
            if summary_config.include_keywords:
                assert "keywords" in summary
                assert isinstance(summary["keywords"], list)

            if summary_config.include_outline:
                assert "outline" in summary
                assert isinstance(summary["outline"], list)

    def test_empty_collection_raises_valueerror(
        self, summary_config: SummaryConfig, db_backend: ChromaDBBackend
    ) -> None:
        """Test that empty collection raises ValueError."""
        generator = SummaryGenerator(summary_config, db_backend)

        # Create an empty collection
        full_collection = f"{summary_config.collection_prefix}_empty_summary"
        db_backend.add_collection(full_collection)

        with pytest.raises(ValueError, match="No documents found"):
            generator.generate("empty_summary")

    def test_nonexistent_collection_raises_valueerror(
        self, summary_config: SummaryConfig, db_backend: ChromaDBBackend
    ) -> None:
        """Test that nonexistent collection raises ValueError."""
        generator = SummaryGenerator(summary_config, db_backend)

        with pytest.raises(ValueError, match="does not exist"):
            generator.generate("nonexistent_summary")


class TestQuizGenerator:
    """Test quiz generator with real document data."""

    def test_generate_from_real_documents(
        self, quiz_config: QuizConfig, db_backend: ChromaDBBackend,
        populated_collection: str
    ) -> None:
        """Test generating quiz from real ingested documents."""
        generator = QuizGenerator(quiz_config, db_backend)

        with patch("tools.rag.embeddings.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.embed_query.return_value = [0.1] * 384

            questions = generator.generate(populated_collection, count=3, difficulty="intermediate")

            # Verify questions were generated
            assert len(questions) > 0
            assert len(questions) <= 3

            # Verify structure
            for q in questions:
                assert "question" in q
                assert "type" in q
                assert "answer" in q
                assert "collection" in q
                assert q["collection"] == populated_collection
                assert q["type"] in ["multiple_choice", "true_false", "short_answer"]

    def test_empty_collection_raises_valueerror(
        self, quiz_config: QuizConfig, db_backend: ChromaDBBackend
    ) -> None:
        """Test that empty collection raises ValueError."""
        generator = QuizGenerator(quiz_config, db_backend)

        # Create an empty collection
        full_collection = f"{quiz_config.collection_prefix}_empty_quiz"
        db_backend.add_collection(full_collection)

        with patch("tools.rag.embeddings.EmbeddingClient") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.embed_query.return_value = [0.1] * 384

            with pytest.raises(ValueError, match="No documents found"):
                generator.generate("empty_quiz")

    def test_nonexistent_collection_raises_valueerror(
        self, quiz_config: QuizConfig, db_backend: ChromaDBBackend
    ) -> None:
        """Test that nonexistent collection raises ValueError."""
        generator = QuizGenerator(quiz_config, db_backend)

        with pytest.raises(ValueError, match="does not exist"):
            generator.generate("nonexistent_quiz")
