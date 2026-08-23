"""Tests for the shared vision OCR HTTP helper."""

from unittest.mock import MagicMock, patch

from tools.ocr_client import ocr_image


def test_ocr_image_posts_base64_and_prompt(tmp_path):
    image = tmp_path / "page.jpg"
    image.write_bytes(b"fake-bytes")

    resp = MagicMock()
    resp.json.return_value = {"message": {"content": "  transcribed  \n"}}
    resp.raise_for_status = MagicMock()

    with patch("tools.ocr_client.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = resp
        mock_client.return_value.__exit__.return_value = False
        text = ocr_image(image, "PROMPT", model="llava", endpoint="http://localhost:11434")

    assert text == "transcribed"
    posted = mock_client.return_value.__enter__.return_value.post.call_args
    assert posted.args[0] == "http://localhost:11434/api/chat"
    payload = posted.kwargs["json"]
    assert payload["model"] == "llava"
    assert payload["messages"][0]["content"] == "PROMPT"
    assert len(payload["messages"][0]["images"]) == 1


def test_ocr_image_skips_oversized_file(tmp_path):
    image = tmp_path / "huge.jpg"
    image.write_bytes(b"x" * (51 * 1024 * 1024))
    with patch("tools.ocr_client.httpx.Client") as mock_client:
        assert ocr_image(image, "PROMPT", model="llava") == ""
        mock_client.assert_not_called()
