"""Agent orchestration for retrieval-augmented responses."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from .config import Config, get_config
from .retriever import HybridRetriever, RetrievedChunk

if TYPE_CHECKING:
    from collections.abc import Iterator


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

    def query(self, *, query: str, collection_name: str) -> tuple[Iterator[str], list[RetrievedChunk]]:
        chunks = self.retriever.retrieve(query=query, collection_name=collection_name)
        prompt = self._build_rag_prompt(query=query, chunks=chunks)
        return self._stream_generation(prompt), chunks

    def critique_writing(self, text: str) -> Iterator[str]:
        prompt = self._build_critique_prompt(text)
        return self._stream_generation(prompt)

    def generate_flashcards(self, collection_name: str) -> Iterator[str]:
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
        return self._stream_generation(prompt)

    def _stream_generation(self, prompt: str) -> Iterator[str]:
        payload = {
            "model": self.config.model.name,
            "prompt": prompt,
            "stream": True,
        }
        timeout = httpx.Timeout(self.config.model.timeout_seconds)
        with httpx.stream(
            "POST",
            self.config.model.endpoint,
            json=payload,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="ignore")
                else:
                    line = raw_line

                data = self._parse_stream_line(line)
                if not data:
                    continue
                if data.get("done"):
                    break

                token = data.get("response")
                if token:
                    yield str(token)

    def _parse_stream_line(self, line: str) -> dict[str, object]:
        cleaned = line.strip()
        if cleaned.startswith("data:"):
            cleaned = cleaned[5:].strip()
        if not cleaned or cleaned == "[DONE]":
            return {}
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

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

    def _build_critique_prompt(self, essay_text: str) -> str:
        return (
            "You are a writing coach. Provide specific, actionable suggestions for improving "
            "clarity, structure, argument strength, and style. Include concrete rewrites when useful.\n\n"
            f"Essay:\n{essay_text}\n\n"
            "Feedback:"
        )
