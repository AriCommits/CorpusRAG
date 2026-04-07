"""LLM response classes."""

from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM backend."""
    text: str
    model: str
    done: bool = True
    prompt_tokens: int | None = None
    completion_tokens: int | None = None