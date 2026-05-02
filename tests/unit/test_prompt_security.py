"""Tests for prompt injection mitigation."""

import sys
from unittest.mock import MagicMock

# httpx is an optional runtime dep not needed for PromptTemplates
if "httpx" not in sys.modules:
    sys.modules["httpx"] = MagicMock()

from llm.prompts import PromptTemplates


def test_rag_prompt_has_untrusted_warning():
    prompt = PromptTemplates.rag_response(
        query="What is X?",
        context_chunks=[{"text": "some content", "source": "test.md", "score": 0.9}],
    )
    assert "untrusted reference material" in prompt.lower()


def test_rag_prompt_has_context_tags():
    prompt = PromptTemplates.rag_response(
        query="test",
        context_chunks=[{"text": "content", "source": "s", "score": 0.5}],
    )
    assert "<CONTEXT" in prompt
    assert "</CONTEXT>" in prompt


def test_rag_prompt_has_query_tags():
    prompt = PromptTemplates.rag_response(
        query="my question",
        context_chunks=[],
    )
    assert "<USER_QUERY>" in prompt
    assert "my question" in prompt
