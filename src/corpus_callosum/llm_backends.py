"""Pluggable LLM backend abstraction.

Supports multiple LLM providers via a unified interface:
- Ollama (default, /api/generate)
- OpenAI-compatible (/v1/chat/completions)
- Anthropic-compatible (/v1/messages)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class LLMBackendType(StrEnum):
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"


@dataclass
class LLMResponse:
    text: str
    model: str
    done: bool = True
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass
class LLMConfig:
    backend: LLMBackendType = LLMBackendType.OLLAMA
    endpoint: str = "http://localhost:11434"
    model: str | None = None  # None = auto-detect from inference endpoint
    timeout_seconds: float = 120.0
    api_key: str | None = None
    fallback_models: list[str] = field(default_factory=list)


class LLMBackend(ABC):
    """Base class for LLM backends."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    def stream_completion(self, prompt: str, *, model: str | None = None) -> Iterator[str]:
        """Stream tokens from the model."""

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        """Stream tokens from a chat model."""


class OllamaBackend(LLMBackend):
    """Ollama /api/generate backend."""

    _cached_default_model: str | None = None

    def stream_completion(self, prompt: str, *, model: str | None = None) -> Iterator[str]:
        model_name = model or self.config.model or self._get_default_model()
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
        }
        yield from self._stream_request(payload)

    def _get_default_model(self) -> str:
        """Auto-detect the first available model from Ollama."""
        if OllamaBackend._cached_default_model:
            return OllamaBackend._cached_default_model

        try:
            response = httpx.get(
                f"{self.config.endpoint}/api/tags",
                timeout=httpx.Timeout(10.0),
            )
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            if models:
                model_name: str = models[0].get("name", "")
                if model_name:
                    OllamaBackend._cached_default_model = model_name
                    logger.info("Auto-detected Ollama model: %s", model_name)
                    return model_name
        except Exception as e:
            logger.warning("Failed to auto-detect Ollama model: %s", e)

        raise ValueError(
            "No model specified and auto-detection failed. "
            "Please specify a model with --model or in the config file, "
            "or ensure Ollama has at least one model installed (ollama pull llama3.2)"
        )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        model_name = model or self.config.model or self._get_default_model()
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
        }
        endpoint = f"{self.config.endpoint}/api/chat"
        timeout = httpx.Timeout(self.config.timeout_seconds)
        with httpx.stream("POST", endpoint, json=payload, timeout=timeout) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                data = self._parse_line(raw_line)
                if data.get("done"):
                    break
                message = data.get("message", {})
                content = message.get("content")
                if content:
                    yield str(content)

    def _stream_request(self, payload: dict[str, Any]) -> Iterator[str]:
        timeout = httpx.Timeout(self.config.timeout_seconds)
        with httpx.stream(
            "POST",
            f"{self.config.endpoint}/api/generate",
            json=payload,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                data = self._parse_line(raw_line)
                if data.get("done"):
                    break
                token = data.get("response")
                if token:
                    yield str(token)

    @staticmethod
    def _parse_line(line: str) -> dict[str, Any]:
        cleaned = line.strip()
        if cleaned.startswith("data:"):
            cleaned = cleaned[5:].strip()
        if not cleaned or cleaned == "[DONE]":
            return {}
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


class OpenAICompatibleBackend(LLMBackend):
    """OpenAI-compatible /v1/chat/completions backend."""

    def stream_completion(self, prompt: str, *, model: str | None = None) -> Iterator[str]:
        messages = [{"role": "user", "content": prompt}]
        yield from self.chat_completion(messages, model=model)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        model_name = model or self.config.model
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
        }
        headers: dict[str, str] = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        timeout = httpx.Timeout(self.config.timeout_seconds)
        endpoint = f"{self.config.endpoint}/v1/chat/completions"
        with httpx.stream(
            "POST",
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                cleaned = raw_line.strip()
                if cleaned.startswith("data:"):
                    cleaned = cleaned[5:].strip()
                if not cleaned or cleaned == "[DONE]":
                    continue
                data = self._parse_line(cleaned)
                if not data:
                    continue
                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield str(content)

    @staticmethod
    def _parse_line(line: str) -> dict[str, Any]:
        try:
            parsed = json.loads(line)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


class AnthropicCompatibleBackend(LLMBackend):
    """Anthropic-compatible /v1/messages backend."""

    def stream_completion(self, prompt: str, *, model: str | None = None) -> Iterator[str]:
        messages = [{"role": "user", "content": prompt}]
        yield from self.chat_completion(messages, model=model)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        model_name = model or self.config.model
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,
        }
        headers: dict[str, str] = {
            "anthropic-version": "2023-06-01",
        }
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        timeout = httpx.Timeout(self.config.timeout_seconds)
        endpoint = f"{self.config.endpoint}/v1/messages"
        with httpx.stream(
            "POST",
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                cleaned = raw_line.strip()
                if not cleaned.startswith("data:"):
                    continue
                cleaned = cleaned[5:].strip()
                if not cleaned or cleaned == "[DONE]":
                    continue
                data = self._parse_line(cleaned)
                if not data:
                    continue
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    text = delta.get("text")
                    if text:
                        yield str(text)

    @staticmethod
    def _parse_line(line: str) -> dict[str, Any]:
        try:
            parsed = json.loads(line)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def create_backend(config: LLMConfig) -> LLMBackend:
    """Factory function to create the appropriate backend."""
    backends: dict[LLMBackendType, type[LLMBackend]] = {
        LLMBackendType.OLLAMA: OllamaBackend,
        LLMBackendType.OPENAI_COMPATIBLE: OpenAICompatibleBackend,
        LLMBackendType.ANTHROPIC_COMPATIBLE: AnthropicCompatibleBackend,
    }
    backend_cls = backends.get(config.backend)
    if backend_cls is None:
        raise ValueError(f"Unknown backend type: {config.backend}")
    return backend_cls(config)
