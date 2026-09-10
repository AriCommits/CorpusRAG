"""Tests for transcript cleaner prompt interpolation."""

from unittest.mock import MagicMock

from tools.video.clean import TranscriptCleaner
from tools.video.config import VideoConfig


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_braces_in_transcript_do_not_raise():
    cfg = VideoConfig.from_dict(
        {
            "llm": {},
            "embedding": {},
            "database": {},
            "paths": {},
            "video": {
                "clean_prompt": "Clean:\n{transcript}\nDone.",
            },
        }
    )
    cleaner = TranscriptCleaner.__new__(TranscriptCleaner)
    cleaner.config = cfg
    cleaner._gates = MagicMock()
    cleaner._gates.llm = _NullLock()
    backend = MagicMock()
    backend.complete.return_value = MagicMock(text="ok")
    cleaner.llm_backend = backend

    text = "hello {not_a_field} and {transcript} world"
    result = cleaner.clean(text)

    assert result == "ok"
    prompt = backend.complete.call_args.args[0]
    assert "{not_a_field}" in prompt
    assert "hello" in prompt
    # The template's {transcript} token is substituted, not left as a literal.
    assert prompt.startswith("Clean:\nhello")
