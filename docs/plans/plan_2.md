# Plan 2: Codebase Audit & RAG Pipeline Upgrade

**Date:** 2026-04-16
**Scope:** Hardcoded variable audit, CLI simplification, feature sprawl cleanup, RAG pipeline refactor per spec.

---

## Part A: Codebase Audit Findings

### A1. Hardcoded Variables (should be configurable via YAML)

| File | Line(s) | Hardcoded Value | Issue |
|------|---------|-----------------|-------|
| `src/config/base.py` | 15 | `model = "llama3"` | Doesn't match YAML (`gemma4:26b-a4b-it-q4_K_M`); fallback default should be `None` or match |
| `src/config/base.py` | 44 | `model = "nomic-embed-text"` | Doesn't match YAML (`embeddinggemma`) |
| `src/tools/video/config.py` | 21 | `clean_model = "qwen3:8b"` | Doesn't match YAML; should inherit from `llm.model` |
| `src/tools/video/config.py` | 22 | `clean_ollama_host = "http://localhost:11434"` | Redundant with `llm.endpoint` |
| `src/tools/video/config.py` | 66-82 | All defaults duplicated in `from_dict()` | DRY violation: defaults appear in both the dataclass fields and the `from_dict()` `.get()` calls |
| `src/tools/rag/config.py` | 12-13 | `size=500, overlap=50` | Doesn't match YAML (`1000`/`200`) |
| `src/tools/rag/config.py` | 20-23 | `top_k_semantic=10, top_k_bm25=10, top_k_final=5, rrf_k=60` | Doesn't match YAML (`25`/`25`/`10`/`80`) |
| `src/tools/flashcards/config.py` | 18 | `max_context_chars = 12000` | Not exposed in YAML |
| `src/tools/quizzes/config.py` | 16-17, 22 | `difficulty_distribution`, `max_context_chars = 12000` | Not exposed in YAML |
| `src/tools/summaries/config.py` | 16 | `max_context_chars = 15000` | Not exposed in YAML |
| `src/llm/backend.py` | 248 | `"max_tokens": 4096` | Anthropic backend hardcodes max_tokens; should read from config |
| `src/llm/backend.py` | 252 | `"anthropic-version": "2023-06-01"` | Should be configurable or at least a named constant |
| `src/mcp_server/server.py` | 49-55 | `requests_per_minute=100, requests_per_hour=1000` | Auth/rate-limit config hardcoded |
| `src/mcp_server/server.py` | 537 | `"version": "0.5.0"` | Hardcoded version in health check |
| `src/mcp_server/server.py` | 496 | `allow_origins=["https://localhost:*"]` | CORS origins hardcoded |
| `src/tools/rag/ingest.py` | 26 | `SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}` | Class constant, not configurable |
| `src/tools/rag/ingest.py` | 39 | `max_file_size_mb: int = 1000` | Hardcoded default parameter |
| `src/orchestrations/lecture_pipeline.py` | 87 | `Path(f"/tmp/...")` | Hardcoded `/tmp`; won't work on Windows; should use `config.paths.scratch_dir` |
| `src/orchestrations/lecture_pipeline.py` | 136 | `video_extensions = [".mp4", ".avi", ...]` | Duplicates `VideoConfig.supported_extensions` but missing `.m4v`, `.zoom` |
| `src/db/management.py` | 99 | `"version": "0.5.0"` | Hardcoded backup version |
| `.docker/docker-compose.yml` | 102, 148 | `CC_LLM_MODEL=llama3` | Hardcoded model in docker env |

**Recommended fix pattern:** Every tool config's `from_dict()` should use the dataclass field default as the single source of truth rather than duplicating defaults in `.get()` calls. Global values like the LLM model should flow from `llm.model` unless a tool-specific override is set.

---

### A2. CLI Entry Points — Redundancy & Simplification

`pyproject.toml` defines **11 separate console_scripts** entry points:

```
corpus              (unified CLI — mounts all subcommands)
corpus-mcp-server   (MCP server)
corpus-rag          (standalone RAG CLI)
corpus-flashcards   (standalone flashcards CLI)
corpus-summaries    (standalone summaries CLI)
corpus-quizzes      (standalone quizzes CLI)
corpus-video        (standalone video CLI)
corpus-orchestrate  (standalone orchestrations CLI)
corpus-db           (standalone DB management CLI)
corpus-secrets      (secrets management)
corpus-api-keys     (API key management)
```

**Problems:**

1. **7 standalone CLIs are fully redundant.** Every one of `corpus-rag`, `corpus-flashcards`, `corpus-summaries`, `corpus-quizzes`, `corpus-video`, `corpus-orchestrate`, `corpus-db` is already available via `corpus rag`, `corpus flashcards`, etc. The standalone entry points add no functionality.

2. **`orchestrate query-kb` and `orchestrate build-kb` overlap with `rag query` and `rag ingest`.** `KnowledgeBaseOrchestrator.build_knowledge_base()` is just a thin wrapper around `RAGIngester.ingest_path()`. `query_knowledge_base()` wraps `RAGAgent.query()`. These are not "orchestrations" — they are aliases.

3. **`corpus-secrets` and `corpus-api-keys`** could be subcommands under `corpus` (e.g., `corpus secrets`, `corpus api-keys`).

**Recommendation:**
- **Keep:** `corpus` (unified), `corpus-mcp-server` (different runtime).
- **Remove from `[project.scripts]`:** All 7 standalone tool CLIs. Users use `corpus <tool>`.
- **Merge:** `corpus-secrets` and `corpus-api-keys` into `corpus` as subcommands.
- **Remove or refactor:** `orchestrate build-kb` and `orchestrate query-kb` — they duplicate RAG.
- Each tool CLI file can keep its `main()` for direct `python -m` usage, but the `[project.scripts]` entry should be removed.

---

### A3. Feature Sprawl, Scope Creep & Dead Code

#### Broken / Non-functional Code

| Issue | Location | Severity |
|-------|----------|----------|
| **Generators return placeholder text, not real documents** | `summaries/generator.py:116`, `quizzes/generator.py:116` | **HIGH** — `_get_representative_documents()` returns hardcoded strings like `"Sample document from {collection}"`. Flashcards, quizzes, and summaries are all generated from fake data. |
| **MCP server will crash at runtime** | `mcp_server/server.py:386,418,155` | **HIGH** — References `video_config.whisper.model` (should be `whisper_model`), `video_config.ollama_cleaning.model` (should be `clean_model`), `rag_config.retrieval.top_k` (should be `top_k_final` or `top_k_semantic`). |
| **`KnowledgeBaseOrchestrator` references wrong attribute names** | `orchestrations/knowledge_base.py:65-66` | **HIGH** — `result.documents_processed` and `result.chunks_created` don't exist on `IngestResult`; correct names are `files_indexed` and `chunks_indexed`. |
| **`ALLOWED_CONFIG_KEYS` rejects valid config** | `config/loader.py:23-34` | **HIGH** — Missing `summaries`, `flashcards`, `quizzes`, `orchestrations`, `dev`. Loading `base.example.yaml` would raise `SecurityError`. |

#### Dead Code & Unused Dependencies

| Issue | Location |
|-------|----------|
| **`src/corpus_callosum/`** directory contains only `__pycache__` `.pyc` files — ghost of a previous module structure | Directory should be deleted |
| **BM25 search stub** — `retriever.py:89-109` returns `[]`; hybrid search just calls semantic | Dead code; `rank-bm25` in dependencies is never imported |
| **`rank-bm25`** in `pyproject.toml` and `requirements.txt` | Unused dependency |
| **Heavy unused deps:** `pydantic`, `typer`, `rich`, `structlog` | Declared but not imported in any `.py` file under `src/` |
| **`python-docx`, `beautifulsoup4`, `markdownify`, `striprtf`** | Only referenced in `__pycache__` of deleted `corpus_callosum/converters/` module |

#### Coupling & Architecture Issues

| Issue | Impact |
|-------|--------|
| **`video/clean.py` uses `ollama` library directly** instead of the `llm.backend` abstraction | Parallel code path; can't switch to OpenAI/Anthropic backend for cleaning |
| **`video/config.py` has its own `clean_ollama_host`** | Redundant with `llm.endpoint`; video cleaning should use the global LLM config |
| **`FlashcardGenerator.generate()` calls `self.db.query()` with a string query** (`line 57`) | `DatabaseBackend.query()` expects an embedding vector, not a string — this would fail at runtime |
| **Config `from_dict()` pattern** is copy-pasted across 5 tool configs with minor variations | Should be a shared mixin or use a generic pattern |

---

## Part B: RAG Pipeline Upgrade Plan

### B0. Current RAG State Assessment

| Component | Current Implementation | Spec Requirement |
|-----------|----------------------|------------------|
| **Chunking** | Naive character-based (`ingest.py:_chunk_text()`) | `MarkdownHeaderTextSplitter` (semantic, header-aware) |
| **Metadata** | Only `source_file`, `chunk_index`, `collection_name` | Tags extracted from markdown, section headers as metadata |
| **Retrieval** | Flat semantic search; BM25/hybrid stubbed | `ParentDocumentRetriever` with parent-child architecture |
| **Vector DB** | `PersistentClient` (SQLite, local) by default | Dockerized ChromaDB via `HttpClient` |
| **Framework** | Raw `httpx` calls to Ollama for embeddings | LangChain for splitting, retrieval, and orchestration |
| **Filtering** | `ChromaDBBackend.query()` accepts `where` but retriever never passes it | CLI `--tag`/`--section` flags mapped to ChromaDB `where` filters |
| **Document Store** | None (no parent storage) | `LocalFileStore` or `InMemoryStore` for parent chunks |

### B1. Dependencies to Add/Update

```
# Add to pyproject.toml [project.dependencies]
langchain>=0.3.0
langchain-community>=0.3.0
langchain-chroma>=0.2.0
```

Verify `chromadb>=1.0.20` is compatible with `langchain-chroma`. Remove `rank-bm25` (unused).

### B2. Docker ChromaDB Setup (Spec 3.1)

**Files to modify:**
- `configs/base.yaml` — change `database.mode` default to `http`
- `src/config/base.py` — update `DatabaseConfig.mode` default to `"http"`
- `.docker/docker-compose.yml` — already has ChromaDB; port mapping needs to align (currently maps `8001:8000` externally)

**New file:**
- `docker-compose.yml` (project root) — lightweight compose with just ChromaDB for local dev:
  ```yaml
  services:
    chromadb:
      image: chromadb/chroma:latest
      ports:
        - "8000:8000"
      volumes:
        - chroma-data:/chroma/chroma
  volumes:
    chroma-data:
  ```

**Code changes in `src/db/chroma.py`:** Already supports both `PersistentClient` and `HttpClient` — no change needed.

### B3. Semantic Markdown Splitting & Tag Extraction (Spec 3.2)

**Files to modify:**
- `src/tools/rag/ingest.py` — replace `_chunk_text()` with LangChain `MarkdownHeaderTextSplitter`

**New file:**
- `src/tools/rag/markdown_parser.py` — custom tag parser

**Implementation:**

```python
# In markdown_parser.py
from langchain.text_splitter import MarkdownHeaderTextSplitter
import re

HEADERS_TO_SPLIT = [
    ("#", "Document Title"),
    ("##", "Primary Section"),
    ("###", "Subsection"),
]

def extract_tags(text: str) -> tuple[str, list[str]]:
    """Extract #tags from bulleted lists under headers.
    
    Returns:
        Tuple of (cleaned_text, tags_list)
    """
    tags = []
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Match lines like "- #tag1 #tag2" or "* #tag1"
        tag_matches = re.findall(r'#(\w+)', line)
        if line.strip().startswith(('-', '*')) and tag_matches:
            # This is a tag line in a bulleted list
            tags.extend(tag_matches)
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines), list(set(tags))

def split_markdown(text: str) -> list[dict]:
    """Split markdown into semantic sections with metadata."""
    # Extract tags first
    cleaned_text, tags = extract_tags(text)
    
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,
    )
    docs = splitter.split_text(cleaned_text)
    
    # Enrich metadata with tags
    for doc in docs:
        doc.metadata["tags"] = tags  # Global tags; per-section tags need refinement
    
    return docs
```

**Changes to `ingest.py`:**
- Replace `_chunk_text()` with call to `split_markdown()`
- Update metadata stored in ChromaDB to include `tags`, `Document Title`, `Primary Section`, `Subsection`

### B4. Parent-Child Retrieval Architecture (Spec 3.3)

**Files to modify:**
- `src/tools/rag/retriever.py` — replace `RAGRetriever` internals with `ParentDocumentRetriever`
- `src/tools/rag/ingest.py` — ingest must store parents in document store and children in ChromaDB
- `src/tools/rag/config.py` — add config for parent/child chunk sizes and document store path

**New YAML config section:**

```yaml
rag:
  chunking:
    # Parent chunks come from MarkdownHeaderTextSplitter (full sections)
    child_chunk_size: 400
    child_chunk_overlap: 50
  retrieval:
    top_k_semantic: 25
    top_k_final: 10
  parent_store:
    type: local_file   # local_file | in_memory
    path: ./parent_store
  collection_prefix: rag
```

**New config dataclass fields:**

```python
@dataclass
class ParentStoreConfig:
    type: str = "local_file"  # local_file | in_memory
    path: Path = field(default_factory=lambda: Path("./parent_store"))

@dataclass
class ChunkingConfig:
    child_chunk_size: int = 400
    child_chunk_overlap: int = 50
    # Parent size is determined by MarkdownHeaderTextSplitter (full sections)
```

**Implementation outline:**

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import LocalFileStore  # or InMemoryStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# During ingestion:
parent_store = LocalFileStore(config.rag.parent_store.path)
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.rag.chunking.child_chunk_size,
    chunk_overlap=config.rag.chunking.child_chunk_overlap,
)
vectorstore = Chroma(
    client=chromadb.HttpClient(host=config.database.host, port=config.database.port),
    collection_name=collection,
    embedding_function=embedding_fn,
)
retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=parent_store,
    child_splitter=child_splitter,
)
retriever.add_documents(parent_docs)  # Parent docs from MarkdownHeaderTextSplitter

# During query:
# retriever.invoke(query) returns PARENT documents, not child chunks
```

### B5. Metadata Pre-Filtering Engine (Spec 3.4)

**Files to modify:**
- `src/tools/rag/cli.py` — add `--tag` and `--section` options to `query` and `chat` commands
- `src/tools/rag/retriever.py` — pass `where` filter to ChromaDB
- `src/tools/rag/agent.py` — accept and forward filter params

**CLI changes:**

```python
@rag.command()
@click.argument("query")
@click.option("--collection", "-c", required=True)
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--section", "-s", default=None, help="Filter by section name")
@click.option("--top-k", "-k", default=None, type=int)
@click.option("--config", "-f", default="configs/base.yaml")
def query(query, collection, tag, section, top_k, config):
    ...
    filters = build_chroma_filter(tags=tag, section=section)
    response = agent.query(query, collection, top_k=top_k, filters=filters)
```

**Filter builder:**

```python
def build_chroma_filter(tags=None, section=None):
    conditions = []
    if tags:
        conditions.append({"tags": {"$in": list(tags)}})
    if section:
        conditions.append({"Primary Section": section})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
```

---

## Part C: Execution Order

### Phase 1: Cleanup & Stabilization (Pre-requisite)

These fixes de-risk the RAG refactor by eliminating broken code and config inconsistencies.

| Step | Task | Files |
|------|------|-------|
| 1.1 | **Fix `ALLOWED_CONFIG_KEYS`** — add `summaries`, `flashcards`, `quizzes`, `orchestrations`, `dev` | `src/config/loader.py` |
| 1.2 | **Fix MCP server attribute errors** — `whisper.model` -> `whisper_model`, `ollama_cleaning.model` -> `clean_model`, `retrieval.top_k` -> `top_k_final` | `src/mcp_server/server.py` |
| 1.3 | **Fix `KnowledgeBaseOrchestrator` attribute names** — `documents_processed` -> `files_indexed`, `chunks_created` -> `chunks_indexed` | `src/orchestrations/knowledge_base.py` |
| 1.4 | **Fix `FlashcardGenerator.generate()` query call** — needs embedding, not string | `src/tools/flashcards/generator.py` |
| 1.5 | **Fix hardcoded `/tmp` path** — use `config.paths.scratch_dir` | `src/orchestrations/lecture_pipeline.py` |
| 1.6 | **Align dataclass defaults with YAML** — make `base.py` defaults match `base.yaml` or use `None` | `src/config/base.py`, all tool `config.py` files |
| 1.7 | **Eliminate duplicate defaults in `from_dict()`** — use `dataclasses.fields()` to auto-apply defaults | All tool `config.py` files |
| 1.8 | **Delete `src/corpus_callosum/`** ghost directory (only contains `.pyc` files) | Directory deletion |
| 1.9 | **Fix `video/clean.py`** — use `llm.backend` abstraction instead of direct `ollama` library, remove redundant `clean_ollama_host` | `src/tools/video/clean.py`, `src/tools/video/config.py` |

### Phase 2: CLI Simplification

| Step | Task | Files |
|------|------|-------|
| 2.1 | **Remove standalone tool entry points** from `[project.scripts]` | `pyproject.toml` |
| 2.2 | **Merge `corpus-secrets` and `corpus-api-keys`** as subcommands under `corpus` | `src/cli.py`, `src/utils/manage_secrets.py`, `src/utils/manage_keys.py` |
| 2.3 | **Remove or merge `orchestrate build-kb` / `query-kb`** — they duplicate `rag ingest` / `rag query` | `src/orchestrations/cli.py`, `src/orchestrations/knowledge_base.py` |

### Phase 3: Dependency Cleanup

| Step | Task | Files |
|------|------|-------|
| 3.1 | **Remove unused deps:** `rank-bm25`, `typer`, `rich`, `structlog`, `pydantic`, `python-docx`, `beautifulsoup4`, `markdownify`, `striprtf` (verify none are actually imported first) | `pyproject.toml`, `requirements.txt` |
| 3.2 | **Add LangChain deps:** `langchain`, `langchain-community`, `langchain-chroma` | `pyproject.toml`, `requirements.txt` |
| 3.3 | **Remove BM25 stub code** from `retriever.py` | `src/tools/rag/retriever.py` |

### Phase 4: RAG Pipeline Refactor

| Step | Task | Files | Spec Ref |
|------|------|-------|----------|
| 4.1 | **Create `docker-compose.yml`** at project root for local ChromaDB | New: `docker-compose.yml` | 3.1 |
| 4.2 | **Update config defaults** — `database.mode: http`, add `rag.parent_store` and `rag.chunking.child_*` | `configs/base.yaml`, `configs/base.example.yaml`, `src/tools/rag/config.py` | 3.1, 3.3 |
| 4.3 | **Create `markdown_parser.py`** — `MarkdownHeaderTextSplitter` + custom tag extractor | New: `src/tools/rag/markdown_parser.py` | 3.2 |
| 4.4 | **Refactor `ingest.py`** — replace `_chunk_text()` with semantic splitting; store parents in `LocalFileStore`, children in ChromaDB via `ParentDocumentRetriever` | `src/tools/rag/ingest.py` | 3.2, 3.3 |
| 4.5 | **Refactor `retriever.py`** — wrap `ParentDocumentRetriever`; accept `where` filters | `src/tools/rag/retriever.py` | 3.3, 3.4 |
| 4.6 | **Add `--tag` / `--section` CLI flags** and filter builder | `src/tools/rag/cli.py` | 3.4 |
| 4.7 | **Update `agent.py`** — forward filter params through query chain | `src/tools/rag/agent.py` | 3.4 |
| 4.8 | **Fix `_get_representative_documents()`** in `summaries/generator.py` and `quizzes/generator.py` — use actual DB retrieval instead of placeholder strings | `src/tools/summaries/generator.py`, `src/tools/quizzes/generator.py` | N/A (pre-existing bug) |

### Phase 5: Verification

| Step | Task |
|------|------|
| 5.1 | **Write integration test** — ingest a sample markdown file with headers and tags, verify parent-child storage, query with tag filter, confirm parent document is returned |
| 5.2 | **Manual end-to-end test** — `docker compose up -d`, `corpus rag ingest ./vault --collection test`, `corpus rag query "what is X" --collection test --tag sometag` |
| 5.3 | **Verify MCP server** — ensure all tool endpoints work with new RAG architecture |

---

## Part D: Coupling & Risk Notes

1. **LangChain is a heavy dependency.** It will become the core of the ingestion and retrieval pipeline. All current `RAGIngester` and `RAGRetriever` logic will be replaced by LangChain wrappers. This is a significant coupling decision — if LangChain's API changes, ingestion and retrieval break.

2. **Parent document store adds state.** The `LocalFileStore` creates a new persistence layer alongside ChromaDB. Both must stay in sync. Consider: what happens if ChromaDB is wiped but the parent store isn't (or vice versa)?  A `corpus rag rebuild` command may be needed.

3. **Docker requirement.** Moving from `PersistentClient` to `HttpClient` as default means users must have Docker running. The fallback `persistent` mode should remain available for simple/offline usage. The config should make this a clear choice.

4. **Tag extraction is fragile.** The spec says tags are "words starting with `#` in bulleted lists under headers." But `#` is also the markdown header marker. The parser must distinguish `# Header` from `- #tag`. The regex approach in B3 handles this by only matching `#word` inside lines starting with `-` or `*`.

5. **The `summaries`, `quizzes`, and `flashcards` generators are non-functional today** because `_get_representative_documents()` returns placeholder strings. Phase 4, Step 4.8 fixes this, but it's independent of the RAG spec and should be prioritized even if the RAG refactor is delayed.
