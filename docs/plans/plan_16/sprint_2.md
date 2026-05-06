# Sprint 2 — Data Structures & Chunking

**Plan:** docs/plans/plan_16/handwriting_ingest_spec.md
**Wave:** 2 of 4
**Can run in parallel with:** none — single agent
**Must complete before:** Sprint 3 (orchestrator imports both modules)

---

## Agents in This Wave

### Agent F: H5 — Postprocessor + Parent-Child Chunker

**Complexity:** M
**Estimated time:** 2 h
**Files to modify:**
- `src/tools/handwriting/postprocessor.py` (NEW) — `ProcessedPage` dataclass, `build_page`, `build_chromadb_metadata` per spec §Step 5.
- `src/tools/handwriting/chunker.py` (NEW) — `HandwritingChildChunk` dataclass, `build_child_chunks` per spec §Step 6.
- `tests/tools/handwriting/test_postprocessor.py` (NEW) — metadata schema correctness, blank detection, content-hash determinism.
- `tests/tools/handwriting/test_chunker.py` (NEW) — context-window slicing, blank-page exclusion, parent_id propagation.

**Depends on:** H1 (`walker.DiscoveredImage`)
**Blocks:** H6 (orchestrator), H7 (CLI)

**Instructions:**

**postprocessor.py:**
- Implement exactly as spec §Step 5. `content_hash` is first 16 hex chars of sha256.
- `is_blank` = `corrected_text.strip() == "[BLANK_PAGE]"`.
- `build_chromadb_metadata` produces flat keys (`folder_depth_0`, `folder_depth_1`, `folder_depth_2`) for the first three levels — Chroma's `where` filters work better on scalar fields than on lists.
- Per spec §ChromaDB Metadata Schema, also include `tag_prefixes` derived from any tag containing `/` (split on first `/`).
- `user_tags` defaults to empty list when None.

**chunker.py:**
- `build_child_chunks` skips pages where `page.is_blank`.
- Context window: `pages[max(0, i-window):min(len, i+window+1)]`, then filter blanks from that window.
- Joiner: `"\n\n---\n\n"` between adjacent page contents.
- Each chunk's metadata is `build_chromadb_metadata(page)` plus `parent_id`.
- Chunk content is the **windowed** content (current page + neighbours), but metadata refers to the **anchor** page.

**Definition of Done:**
- [ ] `ProcessedPage` matches spec schema; `is_blank` correctly set.
- [ ] `build_chromadb_metadata` output has all 13 fields from spec §ChromaDB Metadata Schema (minus `parent_id`, which is added by the chunker).
- [ ] `tag_prefixes` correctly extracted (e.g., `"Year/2020"` → `"Year"`; `"plain"` → not in prefixes).
- [ ] `build_child_chunks` with `context_window=0` produces single-page chunks.
- [ ] `build_child_chunks` with `context_window=1` includes adjacent non-blank pages.
- [ ] Blank pages are excluded entirely (no chunk emitted, not even with `[BLANK_PAGE]` content).
- [ ] Tests pass; uses fake `DiscoveredImage` instances (don't require real files).
