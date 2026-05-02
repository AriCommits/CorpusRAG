# Plan 14 — Video Ingestion Pipeline + MCP Tools

**Status:** Ready for implementation
**Goal:** Add visual OCR pipeline for video content, expose video tools via MCP, support async job execution with status polling, and provide a combined audio+visual pipeline.

---

## Context

CorpusRAG already has Whisper-based audio transcription (`VideoTranscriber`, `TranscriptCleaner`). This plan adds the **visual** side — extracting text/equations from slides, chalkboards, and whiteboards via scene detection + vision OCR. It also wires everything into MCP tools so agentic editors can trigger video processing, and adds a combined pipeline that merges audio transcripts with visual OCR by timestamp.

### User Requirements
- Primary: Visual OCR pipeline (slides, chalkboards, math via Ollama vision models)
- MCP tools for video ingest from local files and YouTube URLs (separate tools)
- Async job execution with polling + MCP-visible progress
- Combined audio+visual pipeline as a third tool
- All models local: Ollama or HuggingFace-based, no external APIs
- pix2tex for math OCR (HuggingFace, local download)

### Existing Infrastructure
- `src/tools/video/` — transcribe.py (Whisper), clean.py (LLM), augment.py, config.py, cli.py
- `src/mcp_server/tools/learn.py` — has `transcribe_video`, `clean_transcript` MCP tools
- `src/mcp_server/profiles.py` — registers tools per profile (dev/learn/full)
- `src/tools/rag/` — RAGAgent with `ingest_text()` for ChromaDB storage
- FFmpeg available as system dependency
- Ollama running locally with `gemma4:26b-a4b-it-q4_K_M` and `embeddinggemma`

---

## Tasks

### V1 — Scene Detection & Frame Extraction
**Complexity:** M
**Depends on:** none
**Files:**
- `src/tools/video/extractor.py` (NEW) — FFmpeg scene change detection, keyframe extraction, timestamp parsing
- `tests/unit/test_extractor.py` (NEW)

**Description:**
Extract keyframes from video files at scene change boundaries using FFmpeg's `select=gt(scene,threshold)` filter. Returns `ExtractedFrame` dataclass with path, frame index, and source timestamp. Includes configurable scene threshold (default 0.3) and minimum interval between frames (default 2s) to prevent burst extraction.

Key implementation details:
- Use `subprocess.run` with `ffmpeg` for frame extraction
- Use `ffprobe` to extract presentation timestamps (pts_time)
- Output frames as JPEG to a temp directory
- `format_timestamp(seconds) -> "HH:MM:SS"` utility
- Fallback to evenly-spaced timestamps if ffprobe parsing fails
- Temp dir under `scratch_dir / video_frames / {video_stem}`

**Definition of Done:**
- [ ] `extract_keyframes(video_path, output_dir, threshold, min_interval) -> list[ExtractedFrame]`
- [ ] `format_timestamp(seconds) -> str`
- [ ] Unit tests with mocked subprocess calls
- [ ] Handles missing ffmpeg gracefully (ImportError-style message)

---

### V2 — Frame Classification
**Complexity:** S
**Depends on:** none
**Files:**
- `src/tools/video/classifier.py` (NEW) — Heuristic frame classifier (slide/chalkboard/whiteboard/no_content)
- `tests/unit/test_classifier.py` (NEW)

**Description:**
Classify extracted frames into `FrameType` enum using pixel-level heuristics (no ML model needed). Uses mean brightness and edge density to distinguish slides (bright, high contrast), chalkboards (dark), whiteboards (mid-range with edges), and no-content frames (uniform, no text).

Key thresholds:
- `mean_brightness < 60` → chalkboard
- `mean_brightness > 180 and std > 40` → slide
- `mean_brightness > 180 and std <= 40` → no_content
- Edge density > 0.05 → whiteboard, else no_content

Only requires PIL and numpy (already in deps).

**Definition of Done:**
- [ ] `FrameType` enum: SLIDE, CHALKBOARD, WHITEBOARD, NO_CONTENT
- [ ] `classify_frame(frame_path) -> FrameType`
- [ ] Unit tests with synthetic test images (solid colors, gradient patterns)
- [ ] No ML model dependencies

---

### V3 — Vision OCR via Ollama
**Complexity:** L
**Depends on:** none
**Files:**
- `src/tools/video/ocr.py` (NEW) — Vision OCR using Ollama multimodal models + pix2tex math fallback
- `tests/unit/test_ocr.py` (NEW)

**Description:**
Send classified frames to an Ollama vision model (default: `llava` or `moondream`) for text extraction. Different prompts for slides vs chalkboard/whiteboard content. Math-heavy output (detected by LaTeX density heuristic) triggers pix2tex fallback for better equation OCR.

Key design:
- `ocr_frame(frame_path, frame_type, model) -> (text, is_math_heavy)` — calls Ollama `/api/chat` with base64 image
- `ocr_frame_latex(frame_path) -> str` — pix2tex for math, lazy-loaded
- `ocr_frame_with_fallback(frame_path, frame_type, model, use_latex_fallback) -> str` — main entry point
- Use `httpx` for Ollama API (consistent with existing codebase), not the `ollama` Python package
- Slide prompt: extract text preserving hierarchy (# for titles, ## for headers, bullets for body)
- Chalkboard prompt: extract text + equations in LaTeX notation
- `[NO_CONTENT]` sentinel for frames with no readable text
- Optional frame upscaling for low-res sources (PIL LANCZOS)

pix2tex is optional — if not installed, skip math fallback silently.

**Definition of Done:**
- [ ] `ocr_frame()`, `ocr_frame_latex()`, `ocr_frame_with_fallback()`
- [ ] Prompts tuned for slide and chalkboard content
- [ ] Math detection heuristic (LaTeX char density > 25%)
- [ ] Unit tests with mocked Ollama responses
- [ ] Graceful degradation when pix2tex not installed

---

### V4 — Post-Processing & Deduplication
**Complexity:** S
**Depends on:** none
**Files:**
- `src/tools/video/postprocessor.py` (NEW) — Dedup, formatting, timestamp attachment
- `tests/unit/test_postprocessor.py` (NEW)

**Description:**
Clean raw OCR output: deduplicate near-identical frames (same slide captured twice), attach timestamp metadata, compute content hashes for incremental sync.

Key design:
- `ProcessedChunk` dataclass: content, frame_index, timestamp_sec/str, source_file, frame_type, content_hash
- `deduplicate_chunks(chunks, threshold=0.85) -> list[ProcessedChunk]` — character trigram Jaccard similarity
- `build_chunk(text, frame, frame_type, source_file) -> ProcessedChunk`
- `format_chunk_markdown(chunk) -> str` — wraps content with HTML comment timestamp annotation

**Definition of Done:**
- [ ] `ProcessedChunk` dataclass
- [ ] Deduplication with configurable similarity threshold
- [ ] Content hash (SHA-256 truncated to 16 chars)
- [ ] Unit tests for dedup (identical, similar, different content)

---

### V5 — Async Job Manager
**Complexity:** M
**Depends on:** none
**Files:**
- `src/tools/video/jobs.py` (NEW) — Job manager with subprocess spawning, status tracking, progress reporting
- `tests/unit/test_jobs.py` (NEW)

**Description:**
Long-running video pipelines (transcription, OCR) need async execution. The job manager spawns pipeline work in a background thread (not subprocess — stays in-process for access to config/db), tracks progress via a shared state dict, and exposes status for MCP polling.

Key design:
- `JobManager` singleton — manages a dict of `JobState` objects
- `JobState` dataclass: job_id (UUID), status (queued/running/complete/failed), progress_pct (0-100), current_step (str), result (dict|None), error (str|None), created_at, updated_at
- `submit(fn, *args, **kwargs) -> job_id` — wraps fn in a thread, fn receives a `progress_callback(pct, step_name)` 
- `get_status(job_id) -> JobState`
- `list_jobs() -> list[JobState]`
- Thread pool with max 2 concurrent video jobs (configurable)
- Jobs auto-expire after 1 hour

**Definition of Done:**
- [ ] `JobManager` with submit/get_status/list_jobs
- [ ] `JobState` dataclass with progress tracking
- [ ] Thread-based execution with progress callback
- [ ] Unit tests for job lifecycle (submit, poll, complete, fail)
- [ ] Thread-safe state access

---

### V6 — Visual OCR Pipeline Orchestrator
**Complexity:** L
**Depends on:** V1, V2, V3, V4
**Files:**
- `src/tools/video/ingest.py` (NEW) — Pipeline orchestrator: video → frames → classify → OCR → dedup → ChromaDB
- `tests/unit/test_ingest.py` (NEW)

**Description:**
Orchestrates the full visual OCR pipeline: extract keyframes → classify → OCR → post-process → build parent-child chunks → ingest into ChromaDB via existing RAGAgent.

Key design:
- `ingest_video(video_path, collection, config, db, progress_cb, **opts) -> VideoIngestResult`
- `VideoIngestResult` dataclass: source_file, frames_extracted, frames_skipped, chunks_stored, duration_sec, collection
- Parent doc = full lecture markdown (all frames concatenated with `---` separators)
- Child chunks = individual frame segments with adjacent frame context (configurable `context_window`)
- ChromaDB metadata: source_file, source_type="video_ocr", frame_index, timestamp_sec, timestamp_str, frame_type, content_hash, parent_id
- Progress callback called at each stage: extracting (0-20%), classifying (20-30%), OCR (30-80%), dedup (80-90%), ingesting (90-100%)
- Cleanup temp frames after ingest (configurable)

**Definition of Done:**
- [ ] Full pipeline from video file to ChromaDB
- [ ] Parent-child chunking with context window
- [ ] Progress callback integration
- [ ] Metadata schema matches spec
- [ ] Unit tests with mocked dependencies (no actual video/Ollama needed)

---

### V7 — YouTube Download Support
**Complexity:** S
**Depends on:** none
**Files:**
- `src/tools/video/download.py` (NEW) — yt-dlp wrapper for YouTube/URL video download
- `tests/unit/test_download.py` (NEW)

**Description:**
Download videos from YouTube (or any yt-dlp supported URL) to a temp directory. Returns the local path for pipeline consumption.

Key design:
- `download_video(url, output_dir) -> DownloadResult`
- `DownloadResult` dataclass: local_path, title, duration_sec, url
- `is_url(path_or_url) -> bool` — detect URL vs local path
- Use `yt-dlp` as subprocess (not Python API — avoids heavy import)
- Download best quality mp4 with audio (for combined pipeline)
- Add `yt-dlp` to `[project.optional-dependencies] video`

**Definition of Done:**
- [ ] `download_video()` with yt-dlp subprocess
- [ ] `is_url()` helper
- [ ] Graceful error when yt-dlp not installed
- [ ] Unit tests with mocked subprocess

---

### V8 — VideoConfig Extension
**Complexity:** S
**Depends on:** none
**Files:**
- `src/tools/video/config.py` (MODIFY) — Add OCR and job config fields
- `configs/base.yaml` (MODIFY) — Add new video config keys
- `tests/unit/test_video_config.py` (NEW)

**Description:**
Extend `VideoConfig` with fields for the visual OCR pipeline and job manager.

New fields:
```python
# OCR settings
vision_model: str = "llava"           # Ollama vision model
scene_threshold: float = 0.3          # FFmpeg scene detection sensitivity
min_frame_interval: float = 2.0       # Min seconds between extracted frames
use_latex_fallback: bool = True       # Enable pix2tex for math
dedup_threshold: float = 0.85         # Jaccard similarity for dedup
context_window: int = 1               # Adjacent frames per child chunk

# Job settings
max_concurrent_jobs: int = 2
job_expiry_seconds: int = 3600

# OCR prompts
slide_ocr_prompt: str = "..."
chalkboard_ocr_prompt: str = "..."
```

Update `from_dict()` to read these from `data["video"]`. Update `configs/base.yaml` with sensible defaults.

**Definition of Done:**
- [ ] New config fields with defaults
- [ ] `from_dict()` reads new fields
- [ ] base.yaml updated
- [ ] Unit test for round-trip config loading

---

### V9 — MCP Video Tools
**Complexity:** L
**Depends on:** V5, V6, V7, V8
**Files:**
- `src/mcp_server/tools/video.py` (NEW) — MCP tool implementations for video pipeline
- `src/mcp_server/profiles.py` (MODIFY) — Register video tools in learn/full profiles
- `tests/unit/test_mcp_video.py` (NEW)

**Description:**
Expose four MCP tools for video processing:

1. **`video_ingest_local(path, collection, vision_model?, scene_threshold?)`** — Ingest a local video file via visual OCR pipeline. Async: returns job_id immediately.

2. **`video_ingest_url(url, collection, vision_model?, scene_threshold?)`** — Download video from YouTube/URL, then run visual OCR pipeline. Async: returns job_id.

3. **`video_combined_pipeline(path_or_url, collection, include_audio?, include_visual?)`** — Combined pipeline: runs Whisper audio transcription AND visual OCR in parallel, merges results by timestamp into unified chunks. Async: returns job_id.

4. **`video_job_status(job_id)`** — Poll job progress. Returns: status, progress_pct, current_step, result (if complete), error (if failed).

5. **`video_list_jobs()`** — List all video jobs with their status.

All async tools use the JobManager from V5. The combined pipeline (tool 3) is the crown jewel — it runs Whisper and OCR concurrently, then merges:
- Audio segments get timestamps from Whisper
- Visual segments get timestamps from frame extraction
- Merge by nearest timestamp: each visual chunk gets the corresponding audio transcript appended
- Result: `[00:25:23] [Slide: "Central Limit Theorem"]\n[Audio]: "So what this means is..."`

Register in `profiles.py` under `register_learn_tools` (and `full`).

**Definition of Done:**
- [ ] 5 MCP tools registered and functional
- [ ] Async execution via JobManager
- [ ] Combined pipeline merges audio + visual by timestamp
- [ ] Progress reporting works through MCP polling
- [ ] Unit tests with mocked pipelines

---

### V10 — CLI Integration
**Complexity:** M
**Depends on:** V6, V7, V8
**Files:**
- `src/tools/video/cli.py` (MODIFY) — Add `corpus video ingest` and `corpus video ingest-url` commands
- `tests/unit/test_video_cli.py` (NEW)

**Description:**
Add CLI commands that mirror the MCP tools:

- `corpus video ingest <path> -c <collection>` — Visual OCR pipeline on local file
  - `--threshold` — scene detection sensitivity
  - `--model` — Ollama vision model
  - `--no-latex` — disable pix2tex
  - `--context-window` — adjacent frames per chunk
  - `--keep-frames` — don't delete temp frames
  - `--combined` — also run Whisper and merge audio+visual

- `corpus video ingest-url <url> -c <collection>` — Download + ingest
  - Same options as above

- `corpus video jobs` — List active/recent video jobs
- `corpus video status <job_id>` — Check job status

CLI commands run synchronously with a progress bar (click.progressbar), unlike MCP which is async.

**Definition of Done:**
- [ ] `corpus video ingest` command with all options
- [ ] `corpus video ingest-url` command
- [ ] `corpus video jobs` and `corpus video status` commands
- [ ] Progress bar during processing
- [ ] Unit tests for CLI argument parsing

---

### V11 — Dependencies & Documentation
**Complexity:** S
**Depends on:** V9, V10
**Files:**
- `pyproject.toml` (MODIFY) — Add video OCR dependencies
- `README.md` (MODIFY) — Update video section
- `src/CLI.md` (MODIFY) — Document new video commands
- `src/mcp_server/README.md` (MODIFY) — Document new MCP video tools

**Description:**
Add new dependencies to the `video` extra:
```toml
video = [
    "faster-whisper>=1.0.0",
    "Pillow>=10.0.0",
    "numpy>=1.24.0",
    "pix2tex>=0.1.2",  # optional, for math OCR
]
```

Note: `yt-dlp` is a system tool (like ffmpeg), not a Python dependency — document as system requirement.

Update documentation to cover:
- New `corpus video ingest` / `ingest-url` commands
- MCP video tools (video_ingest_local, video_ingest_url, video_combined_pipeline, video_job_status, video_list_jobs)
- Configuration options for OCR pipeline
- System requirements (ffmpeg, yt-dlp)

**Definition of Done:**
- [ ] pyproject.toml updated with video deps
- [ ] README video section updated
- [ ] CLI.md documents new commands
- [ ] MCP README documents new tools

---

## File Change Summary

| File | Tasks | Action |
|------|-------|--------|
| `src/tools/video/extractor.py` | V1 | NEW |
| `src/tools/video/classifier.py` | V2 | NEW |
| `src/tools/video/ocr.py` | V3 | NEW |
| `src/tools/video/postprocessor.py` | V4 | NEW |
| `src/tools/video/jobs.py` | V5 | NEW |
| `src/tools/video/ingest.py` | V6 | NEW |
| `src/tools/video/download.py` | V7 | NEW |
| `src/tools/video/config.py` | V8 | MODIFY |
| `src/mcp_server/tools/video.py` | V9 | NEW |
| `src/mcp_server/profiles.py` | V9 | MODIFY |
| `src/tools/video/cli.py` | V10 | MODIFY |
| `pyproject.toml` | V11 | MODIFY |
| `README.md` | V11 | MODIFY |
| `src/CLI.md` | V11 | MODIFY |
| `src/mcp_server/README.md` | V11 | MODIFY |
| `configs/base.yaml` | V8 | MODIFY |
| `tests/unit/test_extractor.py` | V1 | NEW |
| `tests/unit/test_classifier.py` | V2 | NEW |
| `tests/unit/test_ocr.py` | V3 | NEW |
| `tests/unit/test_postprocessor.py` | V4 | NEW |
| `tests/unit/test_jobs.py` | V5 | NEW |
| `tests/unit/test_ingest.py` | V6 | NEW |
| `tests/unit/test_download.py` | V7 | NEW |
| `tests/unit/test_video_config.py` | V8 | NEW |
| `tests/unit/test_mcp_video.py` | V9 | NEW |
| `tests/unit/test_video_cli.py` | V10 | NEW |

---

## Dependency Graph

```
V1 (extractor) ──────┐
V2 (classifier) ─────┤
V3 (ocr) ────────────┼──→ V6 (orchestrator) ──┐
V4 (postprocessor) ──┘                         │
                                                ├──→ V9 (MCP tools) ──→ V11 (docs)
V5 (job manager) ──────────────────────────────┤
V7 (download) ─────────────────────────────────┤
V8 (config) ───────────────────────────────────┤
                                                └──→ V10 (CLI) ──────→ V11 (docs)
```

**Wave 1 (parallel):** V1, V2, V3, V4, V5, V7, V8 — all independent, no file conflicts
**Wave 2 (parallel):** V6, V9 partial (MCP tool stubs + job tools), V10 partial
**Wave 3:** V9 (full integration), V10 (full integration)
**Wave 4:** V11 (docs)
