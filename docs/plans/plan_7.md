# Plan 7: Security Audit, Tag Taxonomy Migration, RAG Modularization & Strategy Config

**Date:** 2026-04-19  
**Status:** Pending  
**Depends on:** Plan 6 (consolidated) Phases 1–3 must be completed first (CI fixes, slash router, RAGSyncer).  
**Scope:** Four interconnected tracks: (1) security hardening of plan_6 changes, (2) hierarchical tag taxonomy with updated metadata schema, (3) RAG pipeline modularization with LangChain vectorstore agnosticism, (4) configurable retrieval strategies with TUI slash commands.

---

## Phase 1: Security Audit of Plan 6 Changes

**Goal:** Identify and remediate security vulnerabilities introduced or exposed by plan_6 implementation (RAGSyncer, `source_file_name` metadata, sync CLI).

### 1.1 — `LocalFileStore` path traversal via `doc_id`

**File:** `src/tools/rag/storage.py`  
**Risk:** HIGH  

`_save_document()` (line 117) and `_load_document()` (line 133) construct file paths using `doc_id` directly:

```python
file_path = self.path / f"{doc_id}.json"
```

If `doc_id` contains path separators (`../`, `..\\`, or absolute paths), an attacker could read/write arbitrary JSON files outside the store directory. While `doc_id` is currently generated via `uuid4()`, the `put()` and `mset()` methods accept arbitrary string keys — any caller passing user-controlled input as a key bypasses this.

**Fix:**
```python
from utils.security import sanitize_filename

def _validate_doc_id(self, doc_id: str) -> str:
    """Sanitize document ID to prevent path traversal."""
    sanitized = sanitize_filename(doc_id)
    if not sanitized or sanitized != doc_id.replace("/", "_").replace("\\", "_"):
        raise ValueError(f"Invalid document ID: {doc_id}")
    # Ensure resolved path stays within store directory
    resolved = (self.path / f"{sanitized}.json").resolve()
    if not str(resolved).startswith(str(self.path.resolve())):
        raise ValueError(f"Document ID would escape store directory: {doc_id}")
    return sanitized
```

Apply `_validate_doc_id()` at the start of `_save_document()`, `_load_document()`, and `delete()`.

### 1.2 — `source_file_name` metadata injection

**File:** `src/tools/rag/ingest.py` (line 166)  
**Risk:** LOW  

`file_path.name` is stored directly as `source_file_name`. On Windows, `Path.name` can contain characters like `;`, `&`, `|` if the filesystem allows them. While this metadata is not used in shell commands, it *is* rendered in TUI and CLI output, and could be used in future export filenames.

**Fix:** Apply `sanitize_filename()` before storing:

```python
from utils.security import sanitize_filename

parent_metadata["source_file_name"] = sanitize_filename(file_path.name)
```

### 1.3 — `RAGSyncer` symlink race condition

**File:** `src/tools/rag/sync.py`  
**Risk:** MEDIUM  

The syncer inherits `_iter_source_files()` from `RAGIngester`, which uses `rglob("*")`. On Linux/macOS, a malicious vault could contain symlinks that point outside the vault to sensitive files. The ingester checks `is_symlink()` on the top-level path but not on recursively discovered files.

**Fix:** Add symlink check during file enumeration:

```python
def _iter_source_files(self, path: Path) -> list[Path]:
    # ... existing logic ...
    files = []
    for ext in self.SUPPORTED_EXTENSIONS:
        for f in path.rglob(f"*{ext}"):
            # Skip symlinks to prevent path traversal
            if f.is_symlink():
                continue
            # Verify resolved path is within the source directory
            if not str(f.resolve()).startswith(str(path.resolve())):
                continue
            files.append(f)
    return sorted(files)
```

### 1.4 — ChromaDB metadata filter injection

**File:** `src/tools/rag/retriever.py` (lines 218–233)  
**Risk:** LOW  

The BM25 keyword search manually interprets `where` filter dicts. If a caller passes a `where` dict with unexpected operator keys (e.g., `$regex`, `$eval`), they are silently ignored rather than rejected. ChromaDB's own query layer handles this safely, but the manual filter in BM25 does not.

**Fix:** Whitelist allowed operators in BM25 metadata filtering:

```python
ALLOWED_METADATA_OPS = {"$contains", "$eq", "$ne", "$in", "$or", "$and"}

def _apply_metadata_filter(self, metadata: dict, where: dict) -> bool:
    """Apply metadata filter with operator whitelisting."""
    for key, value in where.items():
        if key.startswith("$") and key not in ALLOWED_METADATA_OPS:
            raise ValueError(f"Unsupported metadata operator: {key}")
        # ... existing filter logic ...
```

### 1.5 — Hash comparison timing attack

**File:** `src/tools/rag/ingest.py` (line 144)  
**Risk:** NEGLIGIBLE  

`existing_hash == file_hash` uses Python's `==` which is not constant-time. For file content hashes this is not exploitable (attacker gains no advantage from knowing partial hash of file contents), but for consistency with security best practices:

**Fix (optional):** Use `hmac.compare_digest()`:

```python
import hmac
if hmac.compare_digest(existing_hash, file_hash):
    continue
```

### 1.6 — Security audit checklist

- [ ] Patch `LocalFileStore` path traversal (1.1) — **CRITICAL**
- [ ] Sanitize `source_file_name` metadata (1.2)
- [ ] Add symlink checks to `_iter_source_files` (1.3)
- [ ] Whitelist metadata filter operators in BM25 (1.4)
- [ ] Optional: constant-time hash comparison (1.5)
- [ ] Add tests for each vulnerability: path traversal, symlink escape, malicious metadata

---

## Phase 2: Hierarchical Tag Taxonomy Migration

**Goal:** Migrate from flat `#Tag_Name` parsing to hierarchical `#Subject/Subtopic` taxonomy with enriched ChromaDB metadata schema.

### 2.1 — Hierarchical tag parser

**File:** `src/tools/rag/markdown_parser.py`

Replace the flat tag regex `r"#(\w+)"` (line 38) with a hierarchy-aware parser:

```python
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class ParsedTag:
    """A parsed hierarchical tag."""
    full: str          # "Skill/Data_Based_Statistical_Reasoning"
    parts: list[str]   # ["Skill", "Data_Based_Statistical_Reasoning"]
    prefix: str        # "Skill"
    leaf: str          # "Data_Based_Statistical_Reasoning"

def parse_hierarchical_tags(content: str) -> list[ParsedTag]:
    """Extract hierarchical tags (#Subject/Subtopic) from markdown."""
    raw_tags = set()
    for line in content.split("\n"):
        if line.strip().startswith(("-", "*")):
            # Match #Word or #Word/Word/Word (max 3 levels)
            matches = re.findall(r"#([\w]+(?:/[\w]+){0,2})", line)
            raw_tags.update(matches)
    
    parsed = []
    for tag in sorted(raw_tags):
        parts = tag.split("/")
        parsed.append(ParsedTag(
            full=tag,
            parts=parts,
            prefix=parts[0],
            leaf=parts[-1],
        ))
    return parsed

def build_tag_metadata(tags: list[ParsedTag]) -> dict[str, list[str]]:
    """Build ChromaDB-compatible metadata from parsed tags."""
    if not tags:
        return {}
    return {
        "tags": [t.full for t in tags],
        "tag_prefixes": sorted({t.prefix for t in tags}),
        "tag_leaves": sorted({t.leaf for t in tags}),
    }
```

**Why `tag_leaves` instead of `tag_parts`:** ChromaDB stores metadata as flat key-value pairs. Storing all intermediate parts creates large metadata entries for deeply nested tags. `tag_prefixes` (top-level subjects) and `tag_leaves` (most specific topic) cover 95% of filtering use cases. Full hierarchy search can use string prefix matching on `tags`.

**Backward compatibility:** The regex `r"#([\w]+(?:/[\w]+){0,2})"` matches both flat tags (`#Python` → `ParsedTag(full="Python", prefix="Python", leaf="Python")`) and hierarchical tags (`#CS/ML` → `ParsedTag(full="CS/ML", prefix="CS", leaf="ML")`). Existing flat tags continue to work.

### 2.2 — Update `extract_tags_from_text()`

**File:** `src/tools/rag/markdown_parser.py`

Refactor `extract_tags_from_text()` to use the new parser:

```python
def extract_tags_from_text(text: str) -> tuple[str, dict[str, list[str]]]:
    """Extract hierarchical #tags from bulleted lists in markdown.
    
    Returns:
        Tuple of (cleaned_text, tag_metadata_dict)
    """
    parsed_tags = parse_hierarchical_tags(text)
    tag_metadata = build_tag_metadata(parsed_tags)
    return text, tag_metadata  # Keep all lines for LLM context
```

**Breaking change:** Return type changes from `tuple[str, list[str]]` to `tuple[str, dict[str, list[str]]]`. Update all callers.

### 2.3 — Update `split_markdown_semantic()`

**File:** `src/tools/rag/markdown_parser.py` (lines 66–83)

```python
def split_markdown_semantic(text: str) -> list[Document]:
    cleaned_text, tag_metadata = extract_tags_from_text(text)
    
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,
    )
    docs = splitter.split_text(cleaned_text)
    
    for doc in docs:
        if not doc.metadata:
            doc.metadata = {}
        # Merge tag metadata fields into document metadata
        doc.metadata.update(tag_metadata)
    
    return docs
```

### 2.4 — Update metadata schema in ingestion

**File:** `src/tools/rag/ingest.py`

The child metadata inherits from parent metadata (line 188: `metadata = dict(parent_metadata)`), so the new `tags`, `tag_prefixes`, and `tag_leaves` fields propagate automatically to children. No changes needed in ingest.py beyond what's already there.

**Verify:** ChromaDB metadata values must be `str`, `int`, `float`, `bool`, or `list[str]`. The `tags`, `tag_prefixes`, and `tag_leaves` fields are all `list[str]` — compatible.

### 2.5 — Update retrieval filters

**File:** `src/tools/rag/retriever.py` (lines 218–233)

Update the BM25 metadata filter to handle the new tag fields:

```python
def _matches_tag_filter(self, doc_metadata: dict, where: dict) -> bool:
    """Check if document metadata matches tag-related filters."""
    for key in ("tags", "tag_prefixes", "tag_leaves"):
        if key in where:
            condition = where[key]
            doc_values = doc_metadata.get(key, [])
            if isinstance(doc_values, str):
                doc_values = [doc_values]
            if "$contains" in condition:
                if condition["$contains"] not in doc_values:
                    return False
    return True
```

### 2.6 — Update TUI sidebar filters

**File:** `src/tools/rag/tui.py`

The sidebar currently has a tag input field that builds ChromaDB `$contains` filters. Update to support prefix-based filtering:

- If user enters `Skill` → filter by `tag_prefixes: {"$contains": "Skill"}`
- If user enters `Skill/Statistics` → filter by `tags: {"$contains": "Skill/Statistics"}`
- If user enters a leaf like `ML` → filter by `tag_leaves: {"$contains": "ML"}`

Detection heuristic: if the filter value contains `/`, match against `tags`; otherwise try `tag_prefixes` first, fall back to `tag_leaves`.

### 2.7 — `/filter` slash command

**File:** `src/tools/rag/slash_commands.py`

Register via the Phase 2 (plan_6) slash command router:

| Command | Action |
|---------|--------|
| `/filter <subject>` | Set tag prefix filter for subsequent queries (e.g., `/filter Skill`) |
| `/filter <subject/topic>` | Set exact tag filter (e.g., `/filter CS/ML`) |
| `/filter tag:<val> section:<val>` | Combined filter |
| `/filter clear` | Clear all active filters |
| `/filter` (no args) | Show currently active filters |

### 2.8 — Re-ingestion requirement

After deploying the new tag parser, existing collections carry flat metadata. Users must re-ingest:

```bash
corpus collections delete <name>
corpus rag ingest --path ./vault --collection <name>
```

Document this in the README (Phase handled by plan_6 Phase 8).

### 2.9 — Tag taxonomy migration checklist

- [ ] Implement `ParsedTag` dataclass and `parse_hierarchical_tags()` (2.1)
- [ ] Refactor `extract_tags_from_text()` return type (2.2)
- [ ] Update `split_markdown_semantic()` to merge tag metadata (2.3)
- [ ] Verify ChromaDB metadata compatibility (2.4)
- [ ] Update BM25 metadata filter for new fields (2.5)
- [ ] Update TUI sidebar filter logic (2.6)
- [ ] Implement `/filter` slash command (2.7)
- [ ] Write tests: flat tag backward compat, hierarchical parsing, 3-level depth, filter matching

---

## Phase 3: RAG Pipeline Modularization

**Goal:** Reorganize `src/tools/rag/` into a modular architecture where parsing, embedding, retrieval strategies, and vectorstore backends are cleanly separated and swappable. Use LangChain interfaces where they add vectorstore agnosticism.

### 3.1 — Target directory structure

```
src/tools/rag/
├── __init__.py                  # Public API exports
├── agent.py                     # RAGAgent (orchestrator — unchanged)
├── cli.py                       # CLI commands (unchanged)
├── config.py                    # RAGConfig + new StrategyConfig
├── session.py                   # SessionManager (unchanged)
├── slash_commands.py            # Slash command handlers
├── sync.py                      # RAGSyncer (unchanged)
├── tui.py                       # TUI app
├── tui_collections.py           # Collection manager screen
│
├── pipeline/                    # Core pipeline components
│   ├── __init__.py
│   ├── embeddings.py            # EmbeddingClient (moved from ./embeddings.py)
│   ├── parsers.py               # Markdown parser + tag parser (moved from ./markdown_parser.py)
│   ├── splitters.py             # Text splitting config/wrappers
│   └── storage.py               # LocalFileStore (moved from ./storage.py)
│
├── strategies/                  # Pluggable retrieval strategies
│   ├── __init__.py              # Strategy registry + factory
│   ├── base.py                  # AbstractRAGStrategy protocol
│   ├── hybrid.py                # HybridStrategy (vector + BM25 + RRF + reranker)
│   ├── semantic.py              # SemanticStrategy (vector search only)
│   └── keyword.py               # KeywordStrategy (BM25 only)
│
├── vectorstores/                # LangChain-compatible vectorstore adapters
│   ├── __init__.py              # VectorStore factory
│   ├── base.py                  # Protocol/ABC for vectorstore operations
│   ├── chroma_adapter.py        # ChromaDB adapter (wraps existing db.chroma)
│   └── langchain_adapter.py     # Generic LangChain VectorStore adapter
│
└── ingest.py                    # RAGIngester (updated imports)
```

### 3.2 — Strategy abstraction

**File:** `src/tools/rag/strategies/base.py`

```python
from typing import Any, Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class RetrievedDocument:
    """A retrieved parent document."""
    id: str
    text: str
    metadata: dict[str, Any]
    rank: int
    score: float = 0.0

class RAGStrategy(Protocol):
    """Protocol for pluggable RAG retrieval strategies."""
    
    name: str
    
    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve relevant documents using this strategy."""
        ...
    
    def initialize(self, collection: str) -> None:
        """Initialize any indexes or caches for a collection."""
        ...
```

### 3.3 — Extract current retrieval into `HybridStrategy`

**File:** `src/tools/rag/strategies/hybrid.py`

Move the existing `RAGRetriever` logic (vector search, BM25, RRF fusion, cross-encoder reranking) into `HybridStrategy`:

```python
class HybridStrategy:
    """Hybrid retrieval: vector search + BM25 keyword search + RRF fusion + cross-encoder reranking."""
    
    name = "hybrid"
    
    def __init__(self, vectorstore, embedder, parent_store, config):
        self.vectorstore = vectorstore
        self.embedder = embedder
        self.parent_store = parent_store
        self.config = config
        self.bm25_index = None
        self.reranker = None
    
    def retrieve(self, query, collection, top_k, where=None):
        vector_docs = self._vector_search(query, collection, top_k * 2, where)
        keyword_docs = self._keyword_search(query, collection, top_k * 2, where)
        fused = self._rrf_fuse(vector_docs, keyword_docs, top_k * 3)
        return self._rerank(query, fused, top_k)
    
    # _vector_search, _keyword_search, _rrf_fuse, _rerank — moved from retriever.py
```

### 3.4 — `SemanticStrategy` (vector-only)

**File:** `src/tools/rag/strategies/semantic.py`

```python
class SemanticStrategy:
    """Pure vector similarity search with optional reranking."""
    
    name = "semantic"
    
    def retrieve(self, query, collection, top_k, where=None):
        vector_docs = self._vector_search(query, collection, top_k * 3, where)
        return self._rerank(query, vector_docs, top_k)
```

Faster than hybrid (skips BM25 indexing), good for short queries where keyword matching adds noise.

### 3.5 — `KeywordStrategy` (BM25-only)

**File:** `src/tools/rag/strategies/keyword.py`

```python
class KeywordStrategy:
    """BM25 keyword search without embeddings."""
    
    name = "keyword"
    
    def retrieve(self, query, collection, top_k, where=None):
        return self._keyword_search(query, collection, top_k, where)
```

Useful for exact-match queries, code search, or when embedding models are unavailable.

### 3.6 — Strategy registry and factory

**File:** `src/tools/rag/strategies/__init__.py`

```python
_STRATEGIES: dict[str, type] = {}

def register_strategy(name: str, cls: type) -> None:
    _STRATEGIES[name] = cls

def get_strategy(name: str, **kwargs) -> RAGStrategy:
    if name not in _STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(_STRATEGIES.keys())}")
    return _STRATEGIES[name](**kwargs)

# Auto-register built-in strategies
register_strategy("hybrid", HybridStrategy)
register_strategy("semantic", SemanticStrategy)
register_strategy("keyword", KeywordStrategy)
```

### 3.7 — VectorStore abstraction with LangChain

**File:** `src/tools/rag/vectorstores/base.py`

Define the interface that all vectorstore adapters must implement:

```python
from typing import Any, Protocol

class VectorStoreAdapter(Protocol):
    """Protocol for vectorstore operations needed by RAG strategies."""
    
    def add_documents(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadata: list[dict],
        ids: list[str],
    ) -> None: ...
    
    def similarity_search(
        self,
        collection: str,
        query_embedding: list[float],
        k: int,
        where: dict[str, Any] | None = None,
    ) -> list[dict]: ...
    
    def delete_by_metadata(self, collection: str, where: dict) -> None: ...
    def collection_exists(self, name: str) -> bool: ...
    def create_collection(self, name: str) -> None: ...
    def list_collections(self) -> list[str]: ...
    def count_documents(self, collection: str) -> int: ...
    def get_metadata_by_filter(self, collection: str, where: dict, limit: int) -> list[dict]: ...
```

### 3.8 — ChromaDB adapter

**File:** `src/tools/rag/vectorstores/chroma_adapter.py`

Wraps the existing `src/db/chroma.py` `ChromaDBBackend` to conform to `VectorStoreAdapter`:

```python
from db import ChromaDBBackend

class ChromaVectorStore:
    """ChromaDB adapter implementing VectorStoreAdapter protocol."""
    
    def __init__(self, db: ChromaDBBackend):
        self.db = db
    
    def similarity_search(self, collection, query_embedding, k, where=None):
        results = self.db.query(collection, query_embedding, n_results=k, where=where)
        # Normalize ChromaDB response format
        return self._normalize_results(results)
    
    # Delegate remaining methods to self.db
```

### 3.9 — LangChain VectorStore adapter

**File:** `src/tools/rag/vectorstores/langchain_adapter.py`

For users who want to swap in any LangChain-supported vectorstore (Pinecone, Weaviate, Qdrant, FAISS, etc.):

```python
from langchain_core.vectorstores import VectorStore as LCVectorStore

class LangChainVectorStoreAdapter:
    """Adapter that wraps any LangChain VectorStore for use with CorpusRAG strategies."""
    
    def __init__(self, vectorstore: LCVectorStore):
        self.vs = vectorstore
    
    def similarity_search(self, collection, query_embedding, k, where=None):
        # LangChain vectorstores use similarity_search_by_vector
        docs = self.vs.similarity_search_by_vector(query_embedding, k=k, filter=where)
        return [{"id": d.metadata.get("id"), "text": d.page_content, 
                 "metadata": d.metadata, "distance": 0.0} for d in docs]
```

This enables future vectorstore backends without touching strategy code:

```python
# Example: Using Qdrant instead of ChromaDB
from langchain_qdrant import QdrantVectorStore
from tools.rag.vectorstores.langchain_adapter import LangChainVectorStoreAdapter

qdrant_vs = QdrantVectorStore.from_existing(...)
adapter = LangChainVectorStoreAdapter(qdrant_vs)
strategy = HybridStrategy(vectorstore=adapter, ...)
```

### 3.10 — Update `RAGRetriever` to use strategy pattern

**File:** `src/tools/rag/retriever.py`

Refactor `RAGRetriever` from a monolithic class into a thin wrapper:

```python
class RAGRetriever:
    """Retrieve documents using a configured strategy."""
    
    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        self.config = config
        vectorstore = ChromaVectorStore(db)
        embedder = EmbeddingClient(config)
        parent_store = LocalFileStore(str(config.parent_store.path))
        
        strategy_name = config.strategy  # NEW config field
        self.strategy = get_strategy(
            strategy_name,
            vectorstore=vectorstore,
            embedder=embedder,
            parent_store=parent_store,
            config=config,
        )
    
    def retrieve(self, query, collection, top_k=None, where=None):
        if top_k is None:
            top_k = self.config.retrieval.top_k_final
        return self.strategy.retrieve(query, collection, top_k, where)
    
    def set_strategy(self, strategy_name: str) -> None:
        """Switch retrieval strategy at runtime."""
        self.strategy = get_strategy(strategy_name, ...)
```

### 3.11 — Migration of existing files

| Old location | New location | Notes |
|---|---|---|
| `src/tools/rag/embeddings.py` | `src/tools/rag/pipeline/embeddings.py` | Move + re-export from old location for backward compat |
| `src/tools/rag/markdown_parser.py` | `src/tools/rag/pipeline/parsers.py` | Move + add `ParsedTag`, `parse_hierarchical_tags()` |
| `src/tools/rag/storage.py` | `src/tools/rag/pipeline/storage.py` | Move + add path traversal fix from Phase 1 |
| `src/tools/rag/retriever.py` | Refactored into `strategies/hybrid.py` + thin `retriever.py` wrapper | Keep `retriever.py` as public API |

**Import compatibility:** Add re-exports in old locations so existing imports don't break:

```python
# src/tools/rag/embeddings.py (compatibility shim)
from .pipeline.embeddings import EmbeddingClient
__all__ = ["EmbeddingClient"]
```

### 3.12 — Modularization checklist

- [ ] Create `pipeline/` package with `__init__.py`, move embeddings, parsers, storage (3.1, 3.11)
- [ ] Create `strategies/` package with `base.py`, registry, factory (3.2, 3.6)
- [ ] Extract `HybridStrategy` from `retriever.py` (3.3)
- [ ] Implement `SemanticStrategy` (3.4)
- [ ] Implement `KeywordStrategy` (3.5)
- [ ] Create `vectorstores/` package with base, chroma adapter, langchain adapter (3.7–3.9)
- [ ] Refactor `RAGRetriever` to delegate to strategy (3.10)
- [ ] Add backward-compatible import shims (3.11)
- [ ] Update `__init__.py` exports
- [ ] Verify all existing tests pass with new structure

---

## Phase 4: Configurable RAG Strategy

**Goal:** Let users select and switch retrieval strategies via config file, CLI flag, or TUI slash command.

### 4.1 — Add `strategy` field to config

**File:** `configs/base.yaml`

```yaml
rag:
  strategy: hybrid          # hybrid | semantic | keyword
  chunking:
    child_chunk_size: 400
    child_chunk_overlap: 50
  retrieval:
    top_k_semantic: 50
    top_k_bm25: 50
    top_k_final: 25
    rrf_k: 80
  reranking:
    enabled: true
    model: cross-encoder/ms-marco-MiniLM-L-6-v2
  parent_store:
    type: local_file
    path: ./parent_store
  collection_prefix: rag
  vectorstore:
    backend: chromadb       # chromadb | langchain
    # langchain_class: langchain_qdrant.QdrantVectorStore  # only if backend=langchain
```

### 4.2 — Update `RAGConfig` dataclass

**File:** `src/tools/rag/config.py`

```python
@dataclass
class RerankingConfig:
    """Reranking configuration."""
    enabled: bool = True
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

@dataclass
class VectorStoreConfig:
    """VectorStore backend configuration."""
    backend: str = "chromadb"          # chromadb | langchain
    langchain_class: str | None = None  # e.g., "langchain_qdrant.QdrantVectorStore"
    langchain_kwargs: dict = field(default_factory=dict)

@dataclass
class RAGConfig(BaseConfig):
    strategy: str = "hybrid"
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    reranking: RerankingConfig = field(default_factory=RerankingConfig)
    parent_store: ParentStoreConfig = field(default_factory=ParentStoreConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    collection_prefix: str = "rag"
```

### 4.3 — CLI flag for strategy override

**File:** `src/tools/rag/cli.py`

Add `--strategy` flag to `query` and `chat` commands:

```python
@rag.command()
@click.option("--strategy", "-s", type=click.Choice(["hybrid", "semantic", "keyword"]),
              default=None, help="Override retrieval strategy")
def query(question, collection, strategy, config, ...):
    if strategy:
        rag_config.strategy = strategy
    # ... existing logic
```

### 4.4 — `/strategy` slash command

**File:** `src/tools/rag/slash_commands.py`

| Command | Action |
|---------|--------|
| `/strategy` | Show current strategy name and description |
| `/strategy hybrid` | Switch to hybrid retrieval (vector + BM25 + RRF + reranker) |
| `/strategy semantic` | Switch to semantic-only retrieval (faster, no BM25) |
| `/strategy keyword` | Switch to keyword-only retrieval (no embeddings) |

Implementation:

```python
@slash_command("strategy", "View or change the RAG retrieval strategy")
def handle_strategy(args: list[str]) -> SlashCommandResult:
    if not args:
        current = retriever.strategy.name
        return SlashCommandResult(
            type="text",
            content=f"Current strategy: {current}\n\nAvailable: hybrid, semantic, keyword\nUse /strategy <name> to switch.",
        )
    
    strategy_name = args[0].lower()
    try:
        retriever.set_strategy(strategy_name)
        return SlashCommandResult(
            type="toast",
            toast_message=f"Switched to {strategy_name} strategy",
        )
    except ValueError as e:
        return SlashCommandResult(type="error", content=str(e))
```

### 4.5 — Strategy descriptions for `/help`

Each strategy should have a human-readable description shown in `/strategy` output:

| Strategy | Description |
|----------|-------------|
| `hybrid` | Full pipeline: vector similarity + BM25 keywords + Reciprocal Rank Fusion + cross-encoder reranking. Best quality, slowest. |
| `semantic` | Vector similarity search with optional reranking. Good balance of speed and quality for natural language queries. |
| `keyword` | BM25 keyword matching only. Fastest, no embedding calls. Best for exact term matching, code search, or when models are unavailable. |

### 4.6 — Strategy configuration checklist

- [ ] Add `strategy`, `reranking`, `vectorstore` fields to config YAML and dataclass (4.1, 4.2)
- [ ] Update `RAGConfig.from_dict()` to parse new fields
- [ ] Add `--strategy` CLI flag to `query` and `chat` commands (4.3)
- [ ] Implement `/strategy` slash command (4.4)
- [ ] Add strategy descriptions (4.5)
- [ ] Write tests: config parsing, strategy switching, CLI flag override

---

## Phase 5: Verification & Tests

### 5.1 — Security tests

**File:** `tests/security/test_storage_traversal.py` (new)

```python
def test_doc_id_path_traversal_blocked():
    """LocalFileStore rejects doc_id with path traversal."""

def test_doc_id_absolute_path_blocked():
    """LocalFileStore rejects absolute path as doc_id."""

def test_symlink_in_vault_skipped():
    """Symlinks inside vault directory are skipped during ingestion."""

def test_source_file_name_sanitized():
    """source_file_name metadata is sanitized."""
```

### 5.2 — Tag parsing tests

**File:** `tests/unit/test_tag_parser.py` (new)

```python
def test_flat_tag_backward_compat():
    """Flat #Tag still parsed correctly."""

def test_hierarchical_tag_two_levels():
    """#Subject/Topic parsed with correct prefix and leaf."""

def test_hierarchical_tag_three_levels():
    """#Subject/Area/Topic caps at 3 levels."""

def test_mixed_flat_and_hierarchical():
    """Mix of flat and hierarchical tags in same document."""

def test_tag_metadata_fields():
    """build_tag_metadata produces tags, tag_prefixes, tag_leaves."""

def test_chromadb_metadata_compatibility():
    """All tag metadata values are list[str]."""
```

### 5.3 — Strategy tests

**File:** `tests/unit/test_strategies.py` (new)

```python
def test_strategy_registry():
    """Built-in strategies are registered."""

def test_strategy_factory():
    """get_strategy() returns correct strategy type."""

def test_unknown_strategy_raises():
    """get_strategy() raises ValueError for unknown strategy."""

def test_strategy_switch_at_runtime():
    """RAGRetriever.set_strategy() swaps strategy."""

def test_config_strategy_field():
    """RAGConfig.strategy defaults to 'hybrid'."""
```

### 5.4 — Integration tests

```python
def test_hierarchical_tag_ingest_and_retrieve():
    """End-to-end: ingest doc with hierarchical tags, retrieve by prefix filter."""

def test_strategy_switch_affects_results():
    """Different strategies produce different result orderings."""
```

### 5.5 — Local verification

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pytest tests/ -v --ignore=tests/test_smoke.py
```

---

## Dependency Graph

```
Phase 1 (security audit)
    ↓
Phase 2 (tag taxonomy) ← depends on Phase 1 fix to storage.py
    ↓
Phase 3 (modularization) ← moves files touched in Phase 2
    ↓
Phase 4 (strategy config) ← uses strategy pattern from Phase 3
    ↓
Phase 5 (verification)
```

Phases 1 and 2 can be partially parallelized (security fixes are independent of tag parsing), but Phase 3 must wait until both are complete since it reorganizes the files they modify.

---

## File Change Summary

| File | Phase | Action |
|------|-------|--------|
| `src/tools/rag/storage.py` → `pipeline/storage.py` | 1, 3 | Path traversal fix + move |
| `src/tools/rag/ingest.py` | 1 | Sanitize `source_file_name`, symlink checks in `_iter_source_files` |
| `src/tools/rag/retriever.py` | 1, 3 | Whitelist metadata ops + refactor to strategy delegation |
| `src/tools/rag/markdown_parser.py` → `pipeline/parsers.py` | 2, 3 | Hierarchical tag parser + move |
| `src/tools/rag/embeddings.py` → `pipeline/embeddings.py` | 3 | Move |
| `src/tools/rag/pipeline/__init__.py` | 3 | **NEW** |
| `src/tools/rag/pipeline/splitters.py` | 3 | **NEW** — text splitting wrappers |
| `src/tools/rag/strategies/__init__.py` | 3 | **NEW** — registry + factory |
| `src/tools/rag/strategies/base.py` | 3 | **NEW** — `RAGStrategy` protocol |
| `src/tools/rag/strategies/hybrid.py` | 3 | **NEW** — extracted from retriever.py |
| `src/tools/rag/strategies/semantic.py` | 3 | **NEW** — vector-only strategy |
| `src/tools/rag/strategies/keyword.py` | 3 | **NEW** — BM25-only strategy |
| `src/tools/rag/vectorstores/__init__.py` | 3 | **NEW** — factory |
| `src/tools/rag/vectorstores/base.py` | 3 | **NEW** — `VectorStoreAdapter` protocol |
| `src/tools/rag/vectorstores/chroma_adapter.py` | 3 | **NEW** — wraps existing ChromaDBBackend |
| `src/tools/rag/vectorstores/langchain_adapter.py` | 3 | **NEW** — wraps any LangChain VectorStore |
| `src/tools/rag/config.py` | 4 | Add `strategy`, `RerankingConfig`, `VectorStoreConfig` |
| `configs/base.yaml` | 4 | Add `strategy`, `reranking`, `vectorstore` fields |
| `src/tools/rag/cli.py` | 4 | Add `--strategy` flag |
| `src/tools/rag/slash_commands.py` | 2, 4 | `/filter` and `/strategy` slash commands |
| `tests/security/test_storage_traversal.py` | 5 | **NEW** |
| `tests/unit/test_tag_parser.py` | 5 | **NEW** |
| `tests/unit/test_strategies.py` | 5 | **NEW** |

---

## Risks & Notes

- **Breaking change:** `extract_tags_from_text()` return type changes from `tuple[str, list[str]]` to `tuple[str, dict[str, list[str]]]`. All callers must be updated (grep for `extract_tags_from_text` to find them).
- **Re-ingestion required:** Collections created before the tag taxonomy change will have flat metadata. The `corpus rag sync` command won't detect the schema change (file hashes haven't changed). Users must manually delete and re-ingest.
- **LangChain dependency scope:** The LangChain adapter (`langchain_adapter.py`) imports from `langchain_core.vectorstores`. This is already a dependency (used for `Document`). No new packages needed for the adapter itself — specific vectorstore backends (Qdrant, Pinecone, etc.) are optional installs.
- **Strategy switching at runtime** changes retrieval behavior mid-session. The TUI should display the active strategy name in the footer or sidebar so users always know which strategy is active.
- **BM25 index invalidation:** Switching from `hybrid` to `keyword` strategy reuses the same BM25 index. Switching *to* `hybrid` from `semantic` requires building the BM25 index, which loads all parent documents. For large collections, this may take a few seconds — show a spinner.
- **Backward-compatible imports:** The compatibility shims (`src/tools/rag/embeddings.py` re-exporting from `pipeline/`) should be kept for at least one release cycle, then removed.
