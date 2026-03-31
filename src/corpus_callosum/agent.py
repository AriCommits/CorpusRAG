"""Agent orchestration for retrieval-augmented responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .config import Config, get_config
from .llm_backends import LLMBackendType, LLMConfig, create_backend
from .memory import get_conversation
from .retriever import HybridRetriever, RetrievedChunk

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class RagAgent:
    """Coordinates retrieval and generation against a local model endpoint."""

    def __init__(
        self,
        *,
        config: Config | None = None,
        retriever: HybridRetriever | None = None,
    ) -> None:
        self.config = config or get_config()
        self.retriever = retriever or HybridRetriever(config=self.config)
        self._backend = create_backend(self._make_llm_config())

    def _make_llm_config(self) -> LLMConfig:
        return LLMConfig(
            backend=LLMBackendType(self.config.model.backend),
            endpoint=self.config.model.endpoint,
            model=self.config.model.name,
            timeout_seconds=self.config.model.timeout_seconds,
            api_key=self.config.model.api_key,
            fallback_models=list(self.config.model.fallback_models),
        )

    def query(
        self,
        *,
        query: str,
        collection_name: str,
        model: str | None = None,
        session_id: str | None = None,
    ) -> tuple[Iterator[str], list[RetrievedChunk]]:
        chunks = self.retriever.retrieve(query=query, collection_name=collection_name)

        if session_id:
            conversation = get_conversation(session_id)
            conversation.add_message("user", query)
            prompt = self._build_rag_prompt_with_history(
                query=query,
                chunks=chunks,
                history=conversation.to_chat_messages(),
            )
        else:
            prompt = self._build_rag_prompt(query=query, chunks=chunks)

        return self._stream_with_memory(
            prompt=prompt,
            model=model,
            session_id=session_id,
        ), chunks

    def critique_writing(self, text: str, *, model: str | None = None) -> Iterator[str]:
        prompt = self._build_critique_prompt(text)
        return self._stream_generation(prompt, model=model)

    def generate_flashcards(
        self,
        collection_name: str,
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        chunks = self.retriever.collection_documents(collection_name)
        if not chunks:
            raise ValueError(f"No indexed chunks found for collection '{collection_name}'")

        context = "\n\n".join(chunk.text for chunk in chunks)
        limit = self.config.model.max_flashcard_context_chars
        if len(context) > limit:
            context = context[:limit]

        prompt = (
            "Generate study flashcards from the source material. "
            "Output one card per line strictly in this format: question::answer\n\n"
            f"Source material:\n{context}\n"
        )
        return self._stream_generation(prompt, model=model)

    def _stream_with_memory(
        self,
        prompt: str,
        *,
        model: str | None = None,
        session_id: str | None = None,
    ) -> Iterator[str]:
        collected = []
        for token in self._stream_generation(prompt, model=model):
            collected.append(token)
            yield token

        if session_id:
            conversation = get_conversation(session_id)
            conversation.add_message("assistant", "".join(collected))

    def _stream_generation(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        models_to_try = [model] if model else [self.config.model.name]
        if self.config.model.fallback_models:
            models_to_try.extend(self.config.model.fallback_models)

        last_error: Exception | None = None
        for model_name in models_to_try:
            try:
                yield from self._backend.stream_completion(prompt, model=model_name)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Model %s failed, trying fallback: %s",
                    model_name,
                    exc,
                )

        if last_error:
            raise last_error

    def _build_rag_prompt(self, *, query: str, chunks: list[RetrievedChunk]) -> str:
        context_blocks: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            source = chunk.metadata.get("source_file", "unknown")
            context_blocks.append(f"[{idx}] Source: {source}\n{chunk.text}")

        context = "\n\n".join(context_blocks) if context_blocks else "No context retrieved."
        return (
            "You are a helpful study assistant. Use only the provided context when possible. "
            "If context is insufficient, say what is missing.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n"
            "Answer:"
        )

    def _build_rag_prompt_with_history(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]],
    ) -> str:
        context_blocks: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            source = chunk.metadata.get("source_file", "unknown")
            context_blocks.append(f"[{idx}] Source: {source}\n{chunk.text}")

        context = "\n\n".join(context_blocks) if context_blocks else "No context retrieved."
        system = (
            "You are a helpful study assistant. Use only the provided context when possible. "
            "If context is insufficient, say what is missing.\n\n"
            f"Context:\n{context}"
        )

        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})

        return _messages_to_prompt(messages)

    def _build_critique_prompt(self, essay_text: str) -> str:
        return (
            "You are a writing coach. Provide specific, actionable suggestions for improving "
            "clarity, structure, argument strength, and style. Include concrete rewrites when useful.\n\n"
            f"Essay:\n{essay_text}\n\n"
            "Feedback:"
        )


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        parts.append(f"[{role}]\n{content}")
    parts.append("[assistant]\n")
    return "\n\n".join(parts)
