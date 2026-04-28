"""Tests for adaptive content-aware text splitter."""
import pytest
from tools.rag.pipeline.adaptive_splitter import classify_content, adaptive_split


class TestClassifyContent:
    def test_short_text(self):
        assert classify_content("Hello world") == "short"

    def test_empty_text(self):
        assert classify_content("") == "short"

    def test_code_fences(self):
        text = "Some intro\n```python\ndef foo():\n    return 42\n```\n" * 3
        assert classify_content(text) == "code"

    def test_indented_code(self):
        text = "\n".join(["    line " + str(i) for i in range(20)])
        assert classify_content(text) == "code"

    def test_bullet_list(self):
        text = "\n".join([f"- Item {i} with some description text" for i in range(20)])
        assert classify_content(text) == "list"

    def test_numbered_list(self):
        text = "\n".join([f"{i}. Step {i} of the process" for i in range(1, 21)])
        assert classify_content(text) == "list"

    def test_default_mixed(self):
        text = "A regular paragraph. " * 30
        result = classify_content(text)
        assert result in ("default", "prose")


class TestAdaptiveSplit:
    def test_short_returns_whole(self):
        chunks = adaptive_split("Short text")
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_empty_returns_empty(self):
        assert adaptive_split("") == []
        assert adaptive_split("   ") == []

    def test_code_gets_larger_chunks(self):
        code = "```python\n" + "\n".join([f"x_{i} = {i}" for i in range(100)]) + "\n```"
        chunks = adaptive_split(code)
        assert all(len(c) <= 900 for c in chunks)  # 800 + some tolerance

    def test_list_splits_at_markers(self):
        text = "\n".join([f"- Item {i}: " + "word " * 20 for i in range(30)])
        chunks = adaptive_split(text)
        assert len(chunks) > 1

    def test_respects_base_params(self):
        # Single-paragraph text long enough that chunk_size drives the split count.
        # Use spaces as separators so chunk_size is the deciding factor.
        text = "word " * 400  # ~2000 chars, classifies as "default" (single line, but
        # avg_sentence_len check: 400 words / 1 sentence = 400 > 20, BUT non_empty(1) < 400/10=40
        # so it would be "prose". Force "default" by adding a period every 5 words.
        text = " ".join(
            f"word{i}." if i % 5 == 0 else f"word{i}" for i in range(400)
        )  # many sentences → avg_sentence_len low → "default"
        small = adaptive_split(text, base_chunk_size=200, base_overlap=20)
        large = adaptive_split(text, base_chunk_size=800, base_overlap=50)
        assert len(small) > len(large)
