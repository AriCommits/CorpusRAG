# Sprint 2 — Pipeline Orchestrator

**Plan:** docs/plans/plan_14/OVERVIEW.md
**Wave:** 2 of 4
**Can run in parallel with:** none — depends on Wave 1
**Must complete before:** Sprint 3

---

## Agents in This Wave

### Agent A: V6 — Visual OCR Pipeline Orchestrator

**Complexity:** L
**Estimated time:** 3 hours
**Files to modify:**
- `src/tools/video/ingest.py` (NEW) — Full pipeline: video → frames → classify → OCR → dedup → ChromaDB
- `tests/unit/test_ingest.py` (NEW)

**Depends on:** V1 (extractor), V2 (classifier), V3 (ocr), V4 (postprocessor), V8 (config)
**Blocks:** V9 (MCP tools), V10 (CLI)

**Instructions:**
Create `ingest.py` that wires together all Wave 1 components:

```python
def ingest_video(
    video_path: Path,
    collection: str,
    config: VideoConfig,
    db: DatabaseBackend,
    progress_cb: Callable[[int, str], None] | None = None,
    **overrides,  # scene_threshold, vision_model, etc.
) -> VideoIngestResult:
```

Pipeline stages with progress percentages:
1. **Extract keyframes** (0-20%) — `extractor.extract_keyframes()`
2. **Classify frames** (20-30%) — `classifier.classify_frame()` per frame, skip NO_CONTENT
3. **OCR frames** (30-80%) — `ocr.ocr_frame_with_fallback()` per content frame. This is the slowest step — update progress per frame within this range.
4. **Post-process** (80-90%) — `postprocessor.build_chunk()` + `deduplicate_chunks()`
5. **Ingest to ChromaDB** (90-100%) — Use existing RAG ingest path

For ChromaDB ingest, use the database backend directly:
- Get or create collection with `db.get_or_create_collection(collection)`
- Add documents with metadata using `db.add_documents()`
- Parent doc: full concatenated markdown with `source_type: "video_ocr"`
- Child chunks: individual frames with metadata (frame_index, timestamp_sec, timestamp_str, frame_type, content_hash, parent_id)

`VideoIngestResult` dataclass: source_file, frames_extracted, frames_skipped, chunks_stored, duration_sec, collection.

The `progress_cb(pct: int, step: str)` callback is optional — CLI uses it for progress bar, MCP uses it via JobManager. If None, just skip.

Config overrides: allow `scene_threshold`, `vision_model`, `use_latex_fallback`, `context_window`, `dedup_threshold` to be passed as kwargs, falling back to config values.

For tests: mock all dependencies (extractor, classifier, ocr, postprocessor, db). Verify the pipeline calls each stage in order, passes correct args, and returns correct result. Test progress callback is called with increasing percentages.

**Definition of Done:**
- [ ] Full pipeline from video file to ChromaDB
- [ ] Parent-child chunking with context window
- [ ] Progress callback called at each stage
- [ ] Config overrides work
- [ ] Metadata schema: source_file, source_type, frame_index, timestamp_sec, timestamp_str, frame_type, content_hash, parent_id
- [ ] Unit tests with fully mocked dependencies
- [ ] No regressions in existing tests
