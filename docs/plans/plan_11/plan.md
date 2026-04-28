# Plan 11: Adaptive Chunking Strategy

**Status:** Not Started
**Created:** 2026-04-27
**Goal:** Add an adaptive chunking method that adjusts child chunk size based on content characteristics, replacing the fixed `RecursiveCharacterTextSplitter(chunk_size=400)` with a strategy that produces better chunks for heterogeneous document collections.

---

## Problem

The current pipeline uses a fixed child chunk size (400 chars, 50 overlap) for all content. This is suboptimal because:

- **Dense technical content** (code, formulas, definitions) gets split mid-concept at 400 chars
- **Narrative prose** (lecture notes, essays) produces chunks that are too small, losing context
- **Lists and bullet points** get split arbitrarily instead of at list boundaries
- **Short sections** (< 400 chars) that are already semantically complete get padded with content from the next section via overlap

The parent-child architecture already handles the "big picture" via `MarkdownHeaderTextSplitter` (parents are full sections). The problem is specifically in how parents get split into children for vector search.

---

## Current Architecture

```
Document → MarkdownHeaderTextSplitter → Parent Docs (full sections)
                                              ↓
                                    RecursiveCharacterTextSplitter(400, 50)
                                              ↓
                                        Child Chunks → Embed → ChromaDB
```

The adaptive chunking replaces only the child splitting step. Parents and the rest of the pipeline are unchanged.

---

## Design: Content-Aware Child Splitter

Instead of a fixed chunk size, analyze each parent document and choose chunk parameters based on content type:

| Content Type | Detection | Chunk Size | Overlap | Separators |
|-------------|-----------|------------|---------|------------|
| **Code blocks** | ` ``` ` fences, 4-space indent | 800 | 100 | `\n\n`, `\n` |
| **Lists** | Lines starting with `- `, `* `, `1. ` | 600 | 50 | `\n\n`, `\n- `, `\n* `, `\n1. ` |
| **Dense prose** | Avg sentence length > 20 words, few line breaks | 500 | 75 | `\n\n`, `. `, `\n` |
| **Short/structured** | Parent < 400 chars | Keep whole | 0 | (no split) |
| **Default** | Everything else | 400 | 50 | `\n\n`, `\n`, ` ` |

### Key Insight

The adaptive splitter doesn't need to be complex. It classifies each parent into one of ~4 content types using simple heuristics (regex counts, line analysis), then picks the right `RecursiveCharacterTextSplitter` config. No ML, no external deps.

---

## Implementation

### New file: `src/tools/rag/pipeline/adaptive_splitter.py`

```python
"""Adaptive content-aware text splitter for RAG child chunks."""

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class ChunkParams:
    """Parameters for a specific content type."""
    chunk_size: int
    chunk_overlap: int
    separators: list[str]


# Content type presets
PRESETS = {
    "code": ChunkParams(800, 100, ["\n\n", "\n"]),
    "list": ChunkParams(600, 50, ["\n\n", "\n- ", "\n* ", "\n1. ", "\n"]),
    "prose": ChunkParams(500, 75, ["\n\n", ". ", "\n", " "]),
    "short": ChunkParams(0, 0, []),  # sentinel — don't split
    "default": ChunkParams(400, 50, ["\n\n", "\n", " ", ""]),
}


def classify_content(text: str) -> str:
    """Classify text content type using simple heuristics.

    Args:
        text: Parent document text.

    Returns:
        One of: "code", "list", "prose", "short", "default"
    """
    if len(text) < 400:
        return "short"

    lines = text.split("\n")
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return "short"

    # Code: fenced blocks or high ratio of indented lines
    code_fences = text.count("```")
    indented = sum(1 for l in non_empty if l.startswith("    ") or l.startswith("\t"))
    if code_fences >= 2 or (indented / len(non_empty)) > 0.4:
        return "code"

    # Lists: majority of lines start with list markers
    list_lines = sum(1 for l in non_empty if re.match(r"^\s*[-*]\s|^\s*\d+\.\s", l))
    if (list_lines / len(non_empty)) > 0.4:
        return "list"

    # Dense prose: long sentences, few line breaks relative to length
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    avg_sentence_len = len(words) / max(len(sentences), 1)
    if avg_sentence_len > 20 and len(non_empty) < len(words) / 10:
        return "prose"

    return "default"


def adaptive_split(text: str, base_chunk_size: int = 400, base_overlap: int = 50) -> list[str]:
    """Split text using content-aware parameters.

    Args:
        text: Parent document text to split into children.
        base_chunk_size: Base chunk size (used for "default" type, can be overridden by config).
        base_overlap: Base overlap (used for "default" type).

    Returns:
        List of child chunk strings.
    """
    content_type = classify_content(text)
    params = PRESETS[content_type]

    # Short content: return as-is
    if content_type == "short":
        return [text] if text.strip() else []

    # Override default preset with caller's base values
    if content_type == "default":
        params = ChunkParams(base_chunk_size, base_overlap, params.separators)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=params.chunk_size,
        chunk_overlap=params.chunk_overlap,
        separators=params.separators,
    )
    return splitter.split_text(text)
```

### Modify: `src/tools/rag/config.py`

Add `adaptive` field to `ChunkingConfig`:

```python
@dataclass
class ChunkingConfig:
    child_chunk_size: int = 400
    child_chunk_overlap: int = 50
    adaptive: bool = True  # NEW — use content-aware splitting
```

### Modify: `src/tools/rag/ingest.py`

In `RAGIngester.__init__`, conditionally use adaptive splitter:

```python
def __init__(self, config, db):
    ...
    self.use_adaptive = self.config.chunking.adaptive

    # Fallback fixed splitter (used when adaptive=False)
    self.child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=self.config.chunking.child_chunk_size,
        chunk_overlap=self.config.chunking.child_chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
```

In the ingestion loop, replace `self.child_splitter.split_text(parent_doc.page_content)` with:

```python
if self.use_adaptive:
    from .pipeline.adaptive_splitter import adaptive_split
    child_docs = adaptive_split(
        parent_doc.page_content,
        base_chunk_size=self.config.chunking.child_chunk_size,
        base_overlap=self.config.chunking.child_chunk_overlap,
    )
else:
    child_docs = self.child_splitter.split_text(parent_doc.page_content)
```

### Modify: `src/mcp_server/tools/dev.py`

Update `store_text` to also use adaptive splitting when available (same pattern).

### Update: `src/tools/rag/pipeline/__init__.py`

Export the new module:

```python
from .adaptive_splitter import adaptive_split, classify_content
```

---

## Config

```yaml
rag:
  chunking:
    child_chunk_size: 400      # base size (used for "default" content type)
    child_chunk_overlap: 50    # base overlap
    adaptive: true             # enable content-aware splitting
```

Set `adaptive: false` to revert to the fixed splitter behavior.

---

## Tasks

### T1: Create `adaptive_splitter.py`

**File:** `src/tools/rag/pipeline/adaptive_splitter.py` (NEW)
**Test:** `tests/unit/test_adaptive_splitter.py` (NEW)

- [ ] Implement `classify_content()` with 5 content types
- [ ] Implement `adaptive_split()` using `RecursiveCharacterTextSplitter` with type-specific params
- [ ] Test classification: code blocks → "code", bullet lists → "list", short text → "short", long prose → "prose", mixed → "default"
- [ ] Test splitting: short text returns as-is, code gets larger chunks, lists split at markers

### T2: Wire into config and ingester

**Files:** `src/tools/rag/config.py`, `src/tools/rag/ingest.py`, `src/tools/rag/pipeline/__init__.py`
**Test:** `tests/unit/test_adaptive_ingest.py` (NEW)

- [ ] Add `adaptive: bool = True` to `ChunkingConfig`
- [ ] Update `RAGConfig.from_dict()` to parse `adaptive` field
- [ ] Update `RAGIngester` to use `adaptive_split()` when `config.chunking.adaptive` is True
- [ ] Export from `pipeline/__init__.py`
- [ ] Test: adaptive=True uses adaptive_split, adaptive=False uses fixed splitter

### T3: Wire into `store_text` MCP tool

**File:** `src/mcp_server/tools/dev.py`

- [ ] Update `store_text()` to use `adaptive_split()` instead of fixed `RecursiveCharacterTextSplitter`
- [ ] Test: store_text with code content produces larger chunks than store_text with short content

### T4: Update setup wizard default

**File:** `src/setup_wizard.py`

- [ ] Add `adaptive: true` to the `rag.chunking` section in `save_config()`

---

## Files Changed

| File | Task | Action |
|------|------|--------|
| `src/tools/rag/pipeline/adaptive_splitter.py` | T1 | NEW |
| `src/tools/rag/pipeline/__init__.py` | T2 | MODIFY (add export) |
| `src/tools/rag/config.py` | T2 | MODIFY (add adaptive field) |
| `src/tools/rag/ingest.py` | T2 | MODIFY (use adaptive_split) |
| `src/mcp_server/tools/dev.py` | T3 | MODIFY (use adaptive_split in store_text) |
| `src/setup_wizard.py` | T4 | MODIFY (add adaptive to config) |
| `tests/unit/test_adaptive_splitter.py` | T1 | NEW |
| `tests/unit/test_adaptive_ingest.py` | T2 | NEW |

---

## Dependency Graph

```
T1 (adaptive_splitter.py — NEW) ──→ T2 (wire into config/ingest) ──→ T3 (wire into store_text)
                                                                   ──→ T4 (setup wizard default)
```

T1 is independent. T2 depends on T1. T3 and T4 depend on T2 and can run in parallel.

---

## Done When

- [ ] `classify_content()` correctly identifies code, lists, prose, short, and default content
- [ ] `adaptive_split()` produces content-appropriate chunk sizes
- [ ] `corpus rag ingest` uses adaptive splitting by default
- [ ] `store_text` MCP tool uses adaptive splitting
- [ ] `adaptive: false` in config reverts to fixed splitting
- [ ] `corpus setup` generates config with `adaptive: true`
- [ ] All tests pass
