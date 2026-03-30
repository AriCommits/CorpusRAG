# CorpusCallosum Plan 01 (src-only implementation)

## Goal

Implement the complete RAG service **only inside `src/`** so the codebase stays clean and modular from day one.

This plan intentionally limits implementation scope to source code modules. Supporting files (tests, packaging, CI, environment scripts) can be added in later plans.

---

## Scope Guardrails

- Implement code only under `src/`.
- Do not create runtime Python modules at repository root.
- Keep homeschool/Anki concerns separate from core RAG responsibilities.
- Use one ChromaDB instance with multiple collections (e.g., `bio201`, `hist310`, `essays`).
- Prioritize retrieval quality early: semantic + BM25 + RRF.

---

## Target `src/` Layout

```text
src/
  corpus_callosum/
    __init__.py
    config.py
    ingest.py
    retriever.py
    agent.py
    api.py
```

### Module responsibilities

- `config.py`
  - Load and validate config values.
  - Expose a single typed configuration object used by all modules.
  - Keep endpoint/model/chunk/retrieval settings centralized.

- `ingest.py`
  - Read `.md`, `.txt`, `.pdf` files from a path.
  - Chunk text with overlap.
  - Embed with sentence-transformers model from config.
  - Upsert into ChromaDB with metadata:
    - `source_file`
    - `chunk_index`
    - `collection_name`

- `retriever.py`
  - Semantic retrieval from ChromaDB (`top_k_semantic`).
  - BM25 retrieval on collection text (`top_k_bm25`).
  - Reciprocal Rank Fusion merge (`rrf_k`) and return `top_k_final`.
  - Always scope by `collection_name`.

- `agent.py`
  - Query flow: retrieve chunks -> build prompt -> call local LLM endpoint -> stream answer.
  - Provide `critique_writing(text)` for essay feedback without retrieval.
  - Keep prompt templates and model I/O here (not in API layer).

- `api.py`
  - FastAPI app and request/response models.
  - Endpoints:
    - `POST /ingest`
    - `POST /query` (stream response)
    - `POST /flashcards`
    - `POST /critique`
    - `GET /collections`
  - Delegate business logic to `ingest.py`, `retriever.py`, and `agent.py`.

---

## Implementation Phases

## Phase 1 - Core scaffolding in `src/`

Deliverables:

- Create all target modules under `src/corpus_callosum/`.
- Add typed interfaces and clear function signatures.
- Add shared data models (chunk/result payloads) inside existing modules.

Definition of done:

- Every module imports cleanly.
- No circular imports.

---

## Phase 2 - Ingestion + vector indexing

Deliverables:

- File loader for `.md`, `.txt`, `.pdf`.
- Chunker configurable for size/overlap.
- Embedding generation via sentence-transformers.
- ChromaDB write path using collection names.

Definition of done:

- Ingesting a folder produces persisted vectors and metadata for the selected collection.

---

## Phase 3 - Hybrid retrieval

Deliverables:

- Chroma semantic search path implemented.
- BM25 index built from collection documents.
- RRF merge implemented and deterministic.

Definition of done:

- Query returns top ranked chunks from combined semantic + keyword retrieval.

---

## Phase 4 - Agent orchestration

Deliverables:

- Prompt builder that injects top retrieved chunks.
- LLM generation call to local endpoint (model/URL from config).
- Streaming response support.
- `critique_writing(text)` prompt path for essay feedback.

Definition of done:

- Query and critique both produce streamed output through a shared model client.

---

## Phase 5 - API surface

Deliverables:

- FastAPI endpoints wired to module functions.
- Collection list endpoint from Chroma client.
- Flashcard endpoint that converts collection chunks to `question::answer` format via LLM.

Definition of done:

- Service can ingest, query, critique, generate flashcards, and list collections through HTTP.

---

## Design Decisions (locked for this plan)

- **Single ChromaDB, many collections** instead of many databases.
- **Hybrid retrieval first** (semantic + BM25 + RRF) for quality.
- **Model runner via local endpoint** (Ollama now, model-agnostic by config).
- **Thin API layer**; core logic remains in `src/corpus_callosum/*` modules.
- **Homeschool pipeline remains separate** and connects through API seam only.

---

## Immediate Build Order

1. `src/corpus_callosum/config.py`
2. `src/corpus_callosum/ingest.py`
3. `src/corpus_callosum/retriever.py`
4. `src/corpus_callosum/agent.py`
5. `src/corpus_callosum/api.py`

This sequence minimizes rework: retrieval and agent depend on ingestion contracts, and API depends on all three.

---

## Risks and Mitigations

- Embedding dimension mismatch -> lock one embedding model in config per index.
- BM25 tokenization quality -> normalize text consistently during ingest and query.
- Streaming API complexity -> keep one model client abstraction in `agent.py`.
- Responsibility creep -> keep flashcard generation as endpoint orchestration, not retrieval logic.

---

## End State

All production code for the RAG service lives under `src/corpus_callosum/` and supports:

- collection-scoped ingestion,
- hybrid retrieval,
- local LLM answering,
- essay critique,
- flashcard generation via API.

The homeschool system remains independent and optionally syncs notes by calling `POST /ingest`.

---

## Execution Checklist

- [x] Create `src/corpus_callosum/__init__.py`.
- [x] Implement typed config loading in `src/corpus_callosum/config.py`.
- [x] Implement ingestion CLI + chunking + Chroma upsert in `src/corpus_callosum/ingest.py`.
- [x] Implement semantic + BM25 + RRF retrieval in `src/corpus_callosum/retriever.py`.
- [x] Implement query/critique/flashcard orchestration in `src/corpus_callosum/agent.py`.
- [x] Implement FastAPI endpoints in `src/corpus_callosum/api.py`.
- [x] Add committed example config in `configs/corpus_callosum.yaml.example`.
- [x] Add install metadata in `requirements.txt` and `pyproject.toml`.
- [x] Add smoke script in `tests/test_smoke.py`.
- [x] Add run and usage docs in `README.md`.
