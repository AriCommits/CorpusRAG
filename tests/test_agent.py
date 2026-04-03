"""Tests for the RAG agent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from corpus_callosum.agent import RagAgent
from corpus_callosum.retriever import RetrievedChunk


class TestRagAgent:
    """Tests for RagAgent class."""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = MagicMock()
        retriever.retrieve.return_value = [
            RetrievedChunk(
                id="test:doc:0:abc",
                text="This is context about photosynthesis.",
                metadata={"source_file": "biology.md"},
                score=0.5,
            ),
        ]
        retriever.collection_documents.return_value = [
            RetrievedChunk(
                id="test:doc:0:abc",
                text="Biology content for flashcards.",
                metadata={"source_file": "biology.md"},
            ),
        ]
        return retriever

    @pytest.fixture
    def agent(self, mock_retriever):
        """Create an agent with mocked retriever."""
        return RagAgent(retriever=mock_retriever)

    def test_build_rag_prompt(self, agent):
        """Test RAG prompt building."""
        chunks = [
            RetrievedChunk(
                id="1",
                text="Photosynthesis converts light to energy.",
                metadata={"source_file": "bio.md"},
            ),
            RetrievedChunk(
                id="2",
                text="Plants use chlorophyll.",
                metadata={"source_file": "plants.md"},
            ),
        ]

        prompt = agent._build_rag_prompt(query="What is photosynthesis?", chunks=chunks)

        assert "What is photosynthesis?" in prompt
        assert "Photosynthesis converts light to energy." in prompt
        assert "Plants use chlorophyll." in prompt
        assert "bio.md" in prompt
        assert "plants.md" in prompt
        assert "Context:" in prompt

    def test_build_rag_prompt_empty_chunks(self, agent):
        """Test RAG prompt with no chunks."""
        prompt = agent._build_rag_prompt(query="test", chunks=[])

        assert "No context retrieved" in prompt
        assert "test" in prompt

    def test_build_critique_prompt(self, agent):
        """Test critique prompt building."""
        essay = "This is my essay about climate change."
        prompt = agent._build_critique_prompt(essay)

        assert "This is my essay about climate change." in prompt
        assert "writing coach" in prompt.lower()
        assert "Feedback:" in prompt

    def test_query_returns_iterator_and_chunks(self, agent, mock_retriever):
        """Test that query returns a token iterator and chunks."""
        with patch.object(agent, "_stream_generation") as mock_stream:
            mock_stream.return_value = iter(["Hello", " ", "World"])

            _tokens, chunks = agent.query(query="test?", collection_name="test")

            # Verify retriever was called
            mock_retriever.retrieve.assert_called_once_with(query="test?", collection_name="test")

            # Verify chunks are returned
            assert len(chunks) == 1
            assert chunks[0].text == "This is context about photosynthesis."

    def test_critique_writing_returns_iterator(self, agent):
        """Test that critique_writing returns a token iterator."""
        with patch.object(agent, "_stream_generation") as mock_stream:
            mock_stream.return_value = iter(["Good", " ", "essay"])

            _tokens = agent.critique_writing("My essay text")

            # Verify stream was called with critique prompt
            mock_stream.assert_called_once()
            call_args = mock_stream.call_args[0][0]
            assert "My essay text" in call_args

    def test_generate_flashcards_returns_iterator(self, agent, mock_retriever):
        """Test that generate_flashcards returns a token iterator."""
        with patch.object(agent, "_stream_generation") as mock_stream:
            mock_stream.return_value = iter(["Q::A"])

            _tokens = agent.generate_flashcards("test")

            # Verify collection_documents was called
            mock_retriever.collection_documents.assert_called_once_with("test")

    def test_generate_flashcards_empty_collection(self, agent, mock_retriever):
        """Test flashcard generation with empty collection."""
        mock_retriever.collection_documents.return_value = []

        with pytest.raises(ValueError) as exc_info:
            agent.generate_flashcards("empty")

        assert "No indexed chunks found" in str(exc_info.value)

    def test_generate_flashcards_truncates_context(self, agent, mock_retriever):
        """Test that flashcard context is truncated to max chars."""
        # Create chunks with lots of text
        mock_retriever.collection_documents.return_value = [
            RetrievedChunk(
                id=f"chunk:{i}",
                text="A" * 10000,  # Large text
                metadata={},
            )
            for i in range(10)
        ]

        with patch.object(agent, "_stream_generation") as mock_stream:
            mock_stream.return_value = iter(["Q::A"])

            agent.generate_flashcards("large")

            # Verify the prompt was truncated
            call_args = mock_stream.call_args[0][0]
            max_chars = agent.config.model.max_flashcard_context_chars
            # The prompt includes more than just the context, so check it's reasonable
            assert len(call_args) < max_chars + 1000


class TestStreamGeneration:
    """Tests for stream generation with mocked HTTP responses."""

    @pytest.fixture
    def agent(self):
        """Create an agent for stream testing."""
        return RagAgent()

    def test_stream_generation_yields_tokens(self, agent):
        """Test that stream generation yields tokens correctly."""
        mock_response_lines = [
            '{"response": "Hello", "done": false}',
            '{"response": " ", "done": false}',
            '{"response": "World", "done": false}',
            '{"response": "", "done": true}',
        ]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(agent._stream_generation("test prompt"))

            assert tokens == ["Hello", " ", "World"]

    def test_stream_generation_handles_empty_lines(self, agent):
        """Test that empty lines are skipped."""
        mock_response_lines = [
            "",
            '{"response": "token", "done": false}',
            "",
            '{"response": "", "done": true}',
        ]

        with patch("httpx.stream") as mock_stream:
            mock_context = MagicMock()
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = iter(mock_response_lines)
            mock_response.raise_for_status = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_response)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_stream.return_value = mock_context

            tokens = list(agent._stream_generation("test"))

            assert tokens == ["token"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
