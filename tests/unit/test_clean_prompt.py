"""Tests for transcript cleaner prompt interpolation."""

from unittest.mock import MagicMock

from tools.video.clean import TranscriptCleaner, render_clean_prompt
from tools.video.config import VideoConfig


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _cleaner(prompt: str) -> TranscriptCleaner:
    cfg = VideoConfig.from_dict(
        {
            "llm": {},
            "embedding": {},
            "database": {},
            "paths": {},
            "video": {"clean_prompt": prompt},
        }
    )
    cleaner = TranscriptCleaner.__new__(TranscriptCleaner)
    cleaner.config = cfg
    cleaner._gates = MagicMock()
    cleaner._gates.llm = _NullLock()
    backend = MagicMock()
    backend.chat.return_value = MagicMock(text="ok")
    backend.complete.return_value = MagicMock(text="ok")
    cleaner.llm_backend = backend
    return cleaner


def test_braces_in_transcript_do_not_raise():
    cleaner = _cleaner("Clean:\n{transcript}\nDone.")
    text = "hello {not_a_field} and {transcript} world"
    result = cleaner.clean(text)

    assert result == "ok"
    messages = cleaner.llm_backend.chat.call_args.args[0]
    user = messages[1]["content"]
    assert "{not_a_field}" in user
    assert "hello" in user
    assert user.startswith("Clean:\nhello")


def test_missing_placeholder_still_appends_transcript():
    rendered = render_clean_prompt("Clean this. Do not summarize.", "Hi everybody")
    assert "Hi everybody" in rendered
    assert rendered.startswith("Clean this.")


def test_clean_sends_transcript_via_chat_when_yaml_omits_placeholder():
    cleaner = _cleaner("Clean this lecture transcript.\n- Remove filler words")
    cleaner.clean("Hi everybody, welcome to the course.")

    messages = cleaner.llm_backend.chat.call_args.args[0]
    assert messages[0]["role"] == "system"
    user = messages[1]["content"]
    assert "Hi everybody, welcome to the course." in user
