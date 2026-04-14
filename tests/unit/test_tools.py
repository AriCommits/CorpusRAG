"""Tests for tool imports and basic functionality."""



def test_flashcards_imports():
    """Test flashcards tool imports."""
    from tools.flashcards import FlashcardConfig, FlashcardGenerator

    assert FlashcardConfig is not None
    assert FlashcardGenerator is not None


def test_summaries_imports():
    """Test summaries tool imports."""
    from tools.summaries import SummaryConfig, SummaryGenerator

    assert SummaryConfig is not None
    assert SummaryGenerator is not None


def test_quizzes_imports():
    """Test quizzes tool imports."""
    from tools.quizzes import QuizConfig, QuizGenerator

    assert QuizConfig is not None
    assert QuizGenerator is not None


def test_video_imports():
    """Test video tool imports."""
    from tools.video import (
        TranscriptAugmenter,
        TranscriptCleaner,
        VideoConfig,
        VideoTranscriber,
    )

    assert VideoConfig is not None
    assert VideoTranscriber is not None
    assert TranscriptCleaner is not None
    assert TranscriptAugmenter is not None


def test_rag_imports():
    """Test RAG tool imports."""
    from tools.rag import (
        IngestResult,
        RAGAgent,
        RAGConfig,
        RAGIngester,
        RAGRetriever,
        RetrievedChunk,
    )

    assert RAGConfig is not None
    assert RAGAgent is not None
    assert RAGRetriever is not None
    assert RAGIngester is not None
    assert IngestResult is not None
    assert RetrievedChunk is not None


def test_flashcards_config_creation():
    """Test flashcards config from dict."""
    from tools.flashcards import FlashcardConfig

    data = {
        "llm": {"backend": "ollama", "model": "qwen3:8b"},
        "database": {"backend": "chroma", "persist_directory": "./data/chroma"},
        "flashcards": {"cards_per_topic": 20, "format": "anki"},
    }

    config = FlashcardConfig.from_dict(data)
    assert config.cards_per_topic == 20
    assert config.format == "anki"
    assert config.llm.model == "qwen3:8b"


def test_quiz_config_creation():
    """Test quiz config from dict."""
    from tools.quizzes import QuizConfig

    data = {
        "llm": {"backend": "ollama", "model": "qwen3:8b"},
        "database": {"backend": "chroma", "persist_directory": "./data/chroma"},
        "quizzes": {"questions_per_topic": 20, "format": "json"},
    }

    config = QuizConfig.from_dict(data)
    assert config.questions_per_topic == 20
    assert config.format == "json"


def test_video_config_creation():
    """Test video config from dict."""
    from tools.video import VideoConfig

    data = {
        "llm": {"backend": "ollama", "model": "qwen3:8b"},
        "database": {"backend": "chroma", "persist_directory": "./data/chroma"},
        "video": {"whisper_model": "large", "whisper_device": "cpu"},
    }

    config = VideoConfig.from_dict(data)
    assert config.whisper_model == "large"
    assert config.whisper_device == "cpu"


def test_rag_config_creation():
    """Test RAG config from dict."""
    from tools.rag import RAGConfig

    # RAGConfig.from_dict reads "chunking" and "retrieval" as top-level keys
    data = {
        "llm": {"backend": "ollama", "model": "qwen3:8b"},
        "database": {"backend": "chroma", "persist_directory": "./data/chroma"},
        "chunking": {"size": 1000, "overlap": 100},
        "retrieval": {"top_k_semantic": 10},
    }

    config = RAGConfig.from_dict(data)
    assert config.chunking.size == 1000
    assert config.chunking.overlap == 100
    assert config.retrieval.top_k_semantic == 10
