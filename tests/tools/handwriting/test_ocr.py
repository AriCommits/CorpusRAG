"""Tests for handwriting OCR module."""

import base64
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.handwriting.ocr import HANDWRITING_PROMPT, ocr_handwriting


class TestHandwritingPrompt:
    """Test the HANDWRITING_PROMPT constant."""

    def test_prompt_contains_blank_page_marker(self):
        """Verify the prompt contains the [BLANK_PAGE] marker."""
        assert "[BLANK_PAGE]" in HANDWRITING_PROMPT

    def test_prompt_contains_illegible_marker(self):
        """Verify the prompt contains the [illegible] marker."""
        assert "[illegible]" in HANDWRITING_PROMPT

    def test_prompt_contains_diagram_marker(self):
        """Verify the prompt contains the [Diagram: ...] marker."""
        assert "[Diagram:" in HANDWRITING_PROMPT


class TestOcrHandwriting:
    """Test the ocr_handwriting function."""

    def test_ocr_handwriting_base64_encoding(self, tmp_path):
        """Verify that image bytes are read and base64-encoded correctly."""
        # Create a temporary image file with known content
        image_path = tmp_path / "test_image.jpg"
        test_content = b"fake image data"
        image_path.write_bytes(test_content)

        expected_b64 = base64.b64encode(test_content).decode()

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "Sample transcription"}
            }

            ocr_handwriting(image_path)

            # Verify ollama.chat was called
            assert mock_chat.called
            call_args = mock_chat.call_args

            # Verify the images parameter contains the base64-encoded data
            messages = call_args[1]["messages"]
            images = messages[0]["images"]
            assert len(images) == 1
            assert images[0] == expected_b64

            # Verify round-trip: decode the base64 and check it matches original
            decoded = base64.b64decode(images[0])
            assert decoded == test_content

    def test_ocr_handwriting_returns_stripped_content(self, tmp_path):
        """Verify that returned content is stripped of whitespace."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "  Sample transcription with whitespace  \n"}
            }

            result = ocr_handwriting(image_path)

            assert result == "Sample transcription with whitespace"

    def test_ocr_handwriting_uses_correct_model_default(self, tmp_path):
        """Verify that the default model is 'llava'."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "Transcription"}
            }

            ocr_handwriting(image_path)

            # Verify ollama.chat was called with model='llava'
            assert mock_chat.call_args[1]["model"] == "llava"

    def test_ocr_handwriting_uses_custom_model(self, tmp_path):
        """Verify that a custom model parameter is passed correctly."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "Transcription"}
            }

            ocr_handwriting(image_path, model="llava:13b")

            # Verify ollama.chat was called with the custom model
            assert mock_chat.call_args[1]["model"] == "llava:13b"

    def test_ocr_handwriting_prompt_is_correct(self, tmp_path):
        """Verify that the correct prompt is passed to ollama.chat."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "Transcription"}
            }

            ocr_handwriting(image_path)

            # Verify the prompt passed matches HANDWRITING_PROMPT
            call_args = mock_chat.call_args
            messages = call_args[1]["messages"]
            assert messages[0]["content"] == HANDWRITING_PROMPT

    def test_ocr_handwriting_message_structure(self, tmp_path):
        """Verify that the message structure is correct."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "Transcription"}
            }

            ocr_handwriting(image_path)

            call_args = mock_chat.call_args
            messages = call_args[1]["messages"]

            # Verify message structure
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert "content" in messages[0]
            assert "images" in messages[0]
            assert isinstance(messages[0]["images"], list)

    def test_ocr_handwriting_blank_page_response(self, tmp_path):
        """Verify handling of [BLANK_PAGE] response (with whitespace)."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": "  [BLANK_PAGE]  \n"}
            }

            result = ocr_handwriting(image_path)

            # Should strip whitespace but preserve the marker
            assert result == "[BLANK_PAGE]"

    def test_ocr_handwriting_with_illegible_markers(self, tmp_path):
        """Verify that [illegible] markers are preserved."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        content = "Some text [illegible] more text"

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": content}
            }

            result = ocr_handwriting(image_path)

            assert "[illegible]" in result
            assert result == content

    def test_ocr_handwriting_with_diagram_markers(self, tmp_path):
        """Verify that [Diagram: ...] markers are preserved."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        content = "# Section\n[Diagram: a simple circuit diagram]\nText after diagram"

        with patch("src.tools.handwriting.ocr.ollama.chat") as mock_chat:
            mock_chat.return_value = {
                "message": {"content": content}
            }

            result = ocr_handwriting(image_path)

            assert "[Diagram:" in result
            assert result == content
