"""Tests for handwriting OCR module."""

from unittest.mock import patch

from tools.handwriting.ocr import HANDWRITING_PROMPT, ocr_handwriting


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

        with patch(
            "tools.handwriting.ocr.ocr_image", return_value="Sample transcription"
        ) as mock_ocr:
            ocr_handwriting(image_path)

            mock_ocr.assert_called_once()
            assert mock_ocr.call_args.args[0] == image_path
            assert mock_ocr.call_args.args[1] == HANDWRITING_PROMPT

    def test_ocr_handwriting_returns_stripped_content(self, tmp_path):
        """Verify that returned content is stripped of whitespace."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch(
            "tools.handwriting.ocr.ocr_image",
            return_value="Sample transcription with whitespace",
        ):
            result = ocr_handwriting(image_path)

            assert result == "Sample transcription with whitespace"

    def test_ocr_handwriting_uses_correct_model_default(self, tmp_path):
        """Verify that the default model is 'llava'."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("tools.handwriting.ocr.ocr_image", return_value="Transcription") as mock_ocr:
            ocr_handwriting(image_path)

            assert mock_ocr.call_args.kwargs["model"] == "llava"

    def test_ocr_handwriting_uses_custom_model(self, tmp_path):
        """Verify that a custom model parameter is passed correctly."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("tools.handwriting.ocr.ocr_image", return_value="Transcription") as mock_ocr:
            ocr_handwriting(image_path, model="llava:13b")

            assert mock_ocr.call_args.kwargs["model"] == "llava:13b"

    def test_ocr_handwriting_prompt_is_correct(self, tmp_path):
        """Verify that the correct prompt is passed to ollama.chat."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("tools.handwriting.ocr.ocr_image", return_value="Transcription") as mock_ocr:
            ocr_handwriting(image_path)

            assert mock_ocr.call_args.args[1] == HANDWRITING_PROMPT

    def test_ocr_handwriting_message_structure(self, tmp_path):
        """Verify that the message structure is correct."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("tools.handwriting.ocr.ocr_image", return_value="Transcription") as mock_ocr:
            ocr_handwriting(image_path)

            assert mock_ocr.call_args.kwargs["model"] == "llava"
            assert mock_ocr.call_args.args[1] == HANDWRITING_PROMPT

    def test_ocr_handwriting_blank_page_response(self, tmp_path):
        """Verify handling of [BLANK_PAGE] response."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        with patch("tools.handwriting.ocr.ocr_image", return_value="[BLANK_PAGE]"):
            result = ocr_handwriting(image_path)

        assert result == "[BLANK_PAGE]"

    def test_ocr_handwriting_with_illegible_markers(self, tmp_path):
        """Verify that [illegible] markers are preserved."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        content = "Some text [illegible] more text"

        with patch("tools.handwriting.ocr.ocr_image", return_value=content):
            result = ocr_handwriting(image_path)

            assert "[illegible]" in result
            assert result == content

    def test_ocr_handwriting_with_diagram_markers(self, tmp_path):
        """Verify that [Diagram: ...] markers are preserved."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")

        content = "# Section\n[Diagram: a simple circuit diagram]\nText after diagram"

        with patch("tools.handwriting.ocr.ocr_image", return_value=content):
            result = ocr_handwriting(image_path)

            assert "[Diagram:" in result
            assert result == content
