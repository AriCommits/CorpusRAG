# Sprint 3 — Pipeline Orchestrator

**Plan:** docs/plans/plan_16/handwriting_ingest_spec.md
**Wave:** 3 of 4
**Can run in parallel with:** none — single agent
**Must complete before:** Sprint 4 (CLI imports the orchestrator)

---

## Agents in This Wave

### Agent G: H6 — Pipeline Orchestrator

**Complexity:** L
**Estimated time:** 3 h
**Files to modify:**
- `src/tools/handwriting/ingest_handwriting.py` (NEW) — `ingest_handwriting`, `HandwritingIngestResult` per spec §Step 7.
- `tests/tools/handwriting/test_ingest_handwriting.py` (NEW) — end-to-end test with mocked Ollama + fake Agent that records `ingest_text` calls.

**Depends on:** H1, H2, H3, H4, H5
**Blocks:** H7 (CLI)

**Instructions:**

Implement `ingest_handwriting.py` per spec §Step 7. Follow the spec body closely; the only deviations / clarifications:

1. **`agent.get_ingested_hashes(collection)`**: this method may not exist on the current Agent class. Before calling it, check whether it exists; if not, fall back to `set()` (process everything). File a follow-up note in the docstring rather than fixing the Agent here — that's a separate concern.

2. **Logging**: use `logging` (not `print`/`click.echo` — that's the CLI's job in Sprint 4). Progress messages at INFO level; warnings for low-confidence pages.

3. **Folder grouping**: group `processed_pages` by `"/".join(page.folder_hierarchy) or "root"`. Per spec Open Question #1, mirror the original directory structure (folder-scoped parents).

4. **Parent doc ingest**: for each folder group, ingest the concatenated content with `doc_id=f"handwriting:{collection}:{folder_key}"` and metadata `{source_type, folder_key, page_count}`.

5. **Child chunks**: pass the agent through `build_child_chunks(pages, parent_id, context_window)`; each child chunk's `metadata` already contains everything Chroma needs.

6. **Cleanup**: only delete preprocessed temp images from the list `preprocessed_paths`; never touch the original input files.

7. **Per spec Open Question #3 — low-confidence warning file**: in addition to the warning logs, write a `warnings.md` file at the end of the run if `low_confidence_count > 0`. Path: `<root_dir>/.handwriting_warnings.md`. Contents: a markdown bullet list of `relative_path (confidence: 0.XX)` for each flagged page. Include this path in `HandwritingIngestResult` (add a `warnings_file: str | None` field).

8. **`HandwritingIngestResult`**: include all fields from spec plus the new `warnings_file`. Make it a frozen dataclass.

9. **Error handling**: a single failing page should not abort the whole batch. Wrap the OCR + correction block in try/except, log the failure, and continue. Track failures in a `failed_pages: int` field on the result.

**Definition of Done:**
- [ ] Full pipeline runs end-to-end on a tmp directory with 2–3 synthetic images (with mocked OCR/correction).
- [ ] Already-ingested hashes are skipped on a second invocation.
- [ ] Blank pages (both `is_likely_blank` and `[BLANK_PAGE]` OCR output) are skipped without ingestion.
- [ ] Low-confidence pages produce a `warnings.md` at the root.
- [ ] Per-page failures don't abort the run; the result reports `failed_pages` count.
- [ ] Folder-scoped parents are created with stable IDs.
- [ ] Preprocessed temp files are cleaned up when `cleanup_preprocessed=True` and retained when False.
- [ ] Tests pass with a `FakeAgent` whose `ingest_text` records calls.
