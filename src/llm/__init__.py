"""
LLM backend abstraction for Corpus Callosum.

Provides unified access to multiple LLM providers:
- Ollama (local models)
- OpenAI-compatible APIs
- Anthropic-compatible APIs
"""

from .backend import create_backend, LLMBackend
from .config import LLMConfig, LLMBackendType
from .prompts import PromptTemplates
from .response import LLMResponse

__all__ = [
    "LLMBackend",
    "LLMBackendType", 
    "LLMConfig",
    "LLMResponse",
    "PromptTemplates",
    "create_backend",
]