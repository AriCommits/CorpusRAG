"""FastAPI application for CorpusCallosum."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from .agent import RagAgent
from .config import get_config
from .ingest import Ingester
from .retriever import HybridRetriever


app = FastAPI(title="CorpusCallosum API", version="0.1.0")


@lru_cache(maxsize=1)
def _get_ingester() -> Ingester:
    return Ingester()


@lru_cache(maxsize=1)
def _get_agent() -> RagAgent:
    return RagAgent()


@lru_cache(maxsize=1)
def _get_retriever() -> HybridRetriever:
    return HybridRetriever()


class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Directory or file path to ingest")
    collection: str = Field(..., description="Target collection name")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Question to ask")
    collection: str = Field(..., description="Collection to search")


class CritiqueRequest(BaseModel):
    essay_text: str = Field(..., description="Essay text to critique")


class FlashcardsRequest(BaseModel):
    collection: str = Field(..., description="Collection name")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
def ingest(request: IngestRequest) -> JSONResponse:
    ingester = _get_ingester()
    try:
        result = ingester.ingest_path(
            path=request.file_path,
            collection_name=request.collection,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse(
        {
            "collection": result.collection,
            "files_indexed": result.files_indexed,
            "chunks_indexed": result.chunks_indexed,
        }
    )


def _sse_stream(tokens: Iterator[str]) -> Iterator[str]:
    for token in tokens:
        text = str(token)
        lines = text.splitlines() or [""]
        for line in lines:
            yield f"data: {line}\n"
        yield "\n"
    yield "data: [DONE]\n\n"


@app.post("/query")
def query(request: QueryRequest) -> StreamingResponse:
    agent = _get_agent()
    try:
        tokens, _chunks = agent.query(
            query=request.query,
            collection_name=request.collection,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(_sse_stream(tokens), media_type="text/event-stream")


@app.post("/critique")
def critique(request: CritiqueRequest) -> StreamingResponse:
    agent = _get_agent()
    try:
        tokens = agent.critique_writing(request.essay_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(_sse_stream(tokens), media_type="text/event-stream")


@app.post("/flashcards")
def flashcards(request: FlashcardsRequest) -> StreamingResponse:
    agent = _get_agent()
    try:
        tokens = agent.generate_flashcards(request.collection)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(_sse_stream(tokens), media_type="text/event-stream")


@app.get("/collections")
def collections() -> JSONResponse:
    retriever = _get_retriever()
    try:
        names = retriever.list_collections()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"collections": names})


def main() -> None:
    config = get_config()
    uvicorn.run(
        "corpus_callosum.api:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
