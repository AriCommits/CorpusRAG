"""Tests for the handwriting corrector module."""

import pytest
from unittest.mock import patch, MagicMock
from src.tools.handwriting.corrector import (
    correct_ocr_output,
    estimate_correction_confidence,
    CORRECTION_PROMPT,
)


class TestCorrectOCROutput:
    """Test the correct_ocr_output function."""

    def test_short_circuit_blank_page(self):
        """Test that [BLANK_PAGE] is returned unchanged without calling ollama."""
        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            result = correct_ocr_output("[BLANK_PAGE]")
            assert result == "[BLANK_PAGE]"
            mock_gen.assert_not_called()

    def test_short_circuit_empty_string(self):
        """Test that empty string is returned unchanged without calling ollama."""
        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            result = correct_ocr_output("")
            assert result == ""
            mock_gen.assert_not_called()

    def test_short_circuit_whitespace_only(self):
        """Test that whitespace-only string is treated as empty and short-circuits."""
        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            result = correct_ocr_output("   \n\t  ")
            assert result == "   \n\t  "
            mock_gen.assert_not_called()

    def test_correction_with_default_model(self):
        """Test that correction calls ollama.generate with correct parameters."""
        raw_text = "The quikc broun fox jumps"
        corrected_text = "The quick brown fox jumps"

        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            mock_gen.return_value = {"response": f"{corrected_text}   "}

            result = correct_ocr_output(raw_text)

            assert result == corrected_text
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            assert call_args[1]["model"] == "mistral"
            prompt = call_args[1]["prompt"]
            assert raw_text in prompt
            assert "You are correcting handwritten notes" in prompt

    def test_correction_with_custom_model(self):
        """Test that custom model is passed to ollama."""
        raw_text = "Some text to correct"

        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            mock_gen.return_value = {"response": "Corrected"}

            correct_ocr_output(raw_text, model="llama3")

            call_args = mock_gen.call_args
            assert call_args[1]["model"] == "llama3"

    def test_response_stripped(self):
        """Test that response from ollama is stripped of whitespace."""
        raw_text = "Text to correct"

        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            mock_gen.return_value = {"response": "  Corrected text  \n\n"}

            result = correct_ocr_output(raw_text)

            assert result == "Corrected text"

    def test_correction_prompt_contains_raw_text(self):
        """Test that the prompt includes the raw_text placeholder."""
        raw_text = "OCR output here"

        with patch("src.tools.handwriting.corrector.ollama.generate") as mock_gen:
            mock_gen.return_value = {"response": "Corrected"}

            correct_ocr_output(raw_text)

            prompt = mock_gen.call_args[1]["prompt"]
            assert raw_text in prompt
            assert "{raw_text}" not in prompt  # Placeholder should be replaced


class TestEstimateCorrectionConfidence:
    """Test the estimate_correction_confidence function."""

    def test_identical_text(self):
        """Test confidence is 1.0 when raw and corrected are identical."""
        text = "The quick brown fox jumps over the lazy dog"
        confidence = estimate_correction_confidence(text, text)
        assert confidence == 1.0

    def test_empty_raw_text(self):
        """Test that empty raw text returns 0.0."""
        confidence = estimate_correction_confidence("", "some corrected text")
        assert confidence == 0.0

    def test_whitespace_only_raw_text(self):
        """Test that whitespace-only raw text returns 0.0."""
        confidence = estimate_correction_confidence("   \n\t  ", "some corrected text")
        assert confidence == 0.0

    def test_subset_relationship(self):
        """Test that when raw_words is a subset, confidence is 1.0."""
        raw = "quick brown fox"
        corrected = "The quick brown fox jumps over the lazy dog"
        confidence = estimate_correction_confidence(raw, corrected)
        assert confidence == 1.0

    def test_partial_overlap(self):
        """Test confidence with partial word overlap."""
        raw = "the quikc broun fox"  # 4 words
        corrected = "the quick brown fox jumps"
        # raw_words = {"the", "quikc", "broun", "fox"}
        # corrected_words = {"the", "quick", "brown", "fox", "jumps"}
        # overlap = {"the", "fox"} = 2 words
        # confidence = 2 / 4 = 0.5
        confidence = estimate_correction_confidence(raw, corrected)
        assert confidence == 0.5

    def test_case_insensitive(self):
        """Test that comparison is case-insensitive."""
        raw = "The Quick Brown FOX"
        corrected = "the quick brown fox"
        confidence = estimate_correction_confidence(raw, corrected)
        assert confidence == 1.0

    def test_significant_changes(self):
        """Test confidence when significant changes occur."""
        raw = "one two three four"  # 4 words
        corrected = "alpha beta gamma delta epsilon"  # 5 words, none overlap
        confidence = estimate_correction_confidence(raw, corrected)
        # overlap = {} = 0 words
        # confidence = 0 / 4 = 0.0
        assert confidence == 0.0

    def test_partial_word_changes(self):
        """Test confidence with some word preservation."""
        raw = "apple banana cherry date"  # 4 words
        corrected = "apple banana grape elderberry fig"  # 5 words, 2 overlap
        confidence = estimate_correction_confidence(raw, corrected)
        # raw_words = {"apple", "banana", "cherry", "date"}
        # corrected_words = {"apple", "banana", "grape", "elderberry", "fig"}
        # overlap = {"apple", "banana"} = 2 words
        # confidence = 2 / 4 = 0.5
        assert confidence == 0.5

    def test_confidence_bounds(self):
        """Test that confidence is always between 0.0 and 1.0."""
        test_cases = [
            ("hello world", "goodbye world"),
            ("a b c", "x y z"),
            ("test", "test"),
            ("one two three", "one two three four five"),
            ("", "anything"),
        ]
        for raw, corrected in test_cases:
            confidence = estimate_correction_confidence(raw, corrected)
            assert 0.0 <= confidence <= 1.0


class TestCorrectionPrompt:
    """Test the CORRECTION_PROMPT constant."""

    def test_prompt_contains_placeholder(self):
        """Test that the prompt has {raw_text} placeholder."""
        assert "{raw_text}" in CORRECTION_PROMPT

    def test_prompt_format_works(self):
        """Test that the prompt can be formatted with raw_text."""
        test_text = "Some OCR output"
        formatted = CORRECTION_PROMPT.format(raw_text=test_text)
        assert test_text in formatted
        assert "{raw_text}" not in formatted

    def test_prompt_preserves_markers(self):
        """Test that prompt mentions preserving [illegible] and [Diagram] markers."""
        assert "[illegible]" in CORRECTION_PROMPT
        assert "[Diagram:" in CORRECTION_PROMPT

    def test_prompt_mentions_markdown_preservation(self):
        """Test that prompt emphasizes markdown preservation."""
        assert "markdown" in CORRECTION_PROMPT.lower()
