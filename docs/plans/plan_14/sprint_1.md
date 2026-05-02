# Sprint 1 — Foundation Components

**Plan:** docs/plans/plan_14/OVERVIEW.md
**Wave:** 1 of 4
**Can run in parallel with:** none — this is the first wave
**Must complete before:** Sprint 2

---

## Agents in This Wave

All 7 agents can run fully in parallel — zero file conflicts.

### Agent A: V1 — Scene Detection & Frame Extraction

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/video/extractor.py` (NEW) — FFmpeg scene change detection, keyframe extraction
- `tests/unit/test_extractor.py` (NEW) — Unit tests with mocked subprocess

**Depends on:** none
**Blocks:** V6 (orchestrator)

**Instructions:**
Create `extractor.py` with:
- `ExtractedFrame` dataclass: `path: Path`, `frame_index: int`, `source_timestamp_sec: float`
- `extract_keyframes(video_path, output_dir, scene_threshold=0.3, min_interval_sec=2.0) -> list[ExtractedFrame]`
  - Uses `subprocess.run` with ffmpeg `select=gt(scene,{threshold})` filter
  - Uses `ffprobe` to extract pts_time for timestamps
  - Falls back to evenly-spaced timestamps if ffprobe parsing fails
  - Output pattern: `frame_%06d.jpg`
- `format_timestamp(seconds: float) -> str` — returns `"HH:MM:SS"`
- Raise clear error if ffmpeg not found on PATH

For tests, mock `subprocess.run` and `subprocess.CompletedProcess`. Create a few fake frame files in a tmp dir to test the glob/sorting logic. Test timestamp parsing with sample ffprobe output.

**Definition of Done:**
- [ ] `extract_keyframes()` works with mocked ffmpeg
- [ ] `format_timestamp()` handles edge cases (0, 3661, etc.)
- [ ] Graceful error when ffmpeg missing
- [ ] Tests pass

---

### Agent B: V2 — Frame Classification

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/video/classifier.py` (NEW) — Heuristic pixel-based classifier
- `tests/unit/test_classifier.py` (NEW) — Tests with synthetic images

**Depends on:** none
**Blocks:** V6 (orchestrator)

**Instructions:**
Create `classifier.py` with:
- `FrameType` enum: `SLIDE`, `CHALKBOARD`, `WHITEBOARD`, `NO_CONTENT`
- `classify_frame(frame_path: Path) -> FrameType`
  - Open with PIL, convert to RGB numpy array
  - `mean_brightness < 60` → CHALKBOARD
  - `mean_brightness > 180 and std > 40` → SLIDE
  - `mean_brightness > 180 and std <= 40` → NO_CONTENT
  - Else: compute edge density via simple Sobel (np.diff). If > 0.05 → WHITEBOARD, else NO_CONTENT
- `_edge_density(arr: np.ndarray) -> float` — horizontal + vertical gradient mean / 255

For tests, create synthetic images with PIL:
- Solid black (50x50) → CHALKBOARD
- White with black text-like patterns → SLIDE
- Solid white → NO_CONTENT
- Mid-gray with edges → WHITEBOARD

**Definition of Done:**
- [ ] All 4 frame types correctly classified on synthetic images
- [ ] No ML model dependencies (PIL + numpy only)
- [ ] Tests pass

---

### Agent C: V3 — Vision OCR via Ollama

**Complexity:** L
**Estimated time:** 3 hours
**Files to modify:**
- `src/tools/video/ocr.py` (NEW) — Ollama vision OCR + pix2tex fallback
- `tests/unit/test_ocr.py` (NEW) — Tests with mocked HTTP responses

**Depends on:** none
**Blocks:** V6 (orchestrator)

**Instructions:**
Create `ocr.py` with:
- `SLIDE_PROMPT` and `CHALKBOARD_PROMPT` constants — see starter spec for exact text
- `ocr_frame(frame_path, frame_type, model, endpoint) -> tuple[str, bool]`
  - Read image, base64 encode
  - POST to `{endpoint}/api/chat` with model, messages containing image
  - Use `httpx` (already in project deps), not the `ollama` package
  - Return (text, is_math_heavy) where is_math_heavy = LaTeX char density > 0.25
- `ocr_frame_latex(frame_path) -> str`
  - Lazy-load pix2tex `LatexOCR` (module-level `_latex_model = None`)
  - Wrap result in `$$\n{latex}\n$$`
  - Return empty string on failure
  - If pix2tex not installed, return empty string (no crash)
- `ocr_frame_with_fallback(frame_path, frame_type, model, endpoint, use_latex_fallback) -> str`
  - Main entry point. Calls ocr_frame, optionally runs pix2tex on math-heavy chalkboard/whiteboard frames
  - Returns `"[NO_CONTENT]"` sentinel for empty frames

Import `FrameType` from `classifier.py` — this is fine since classifier has no heavy deps.

For tests, mock `httpx.Client.post` to return fake Ollama responses. Test math detection heuristic. Test pix2tex fallback path with mock.

**Definition of Done:**
- [ ] Ollama vision OCR works with httpx
- [ ] Math detection heuristic triggers pix2tex
- [ ] Graceful when pix2tex not installed
- [ ] `[NO_CONTENT]` sentinel handled
- [ ] Tests pass with mocked HTTP

---

### Agent D: V4 — Post-Processing & Deduplication

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/video/postprocessor.py` (NEW) — Dedup, formatting, hashing
- `tests/unit/test_postprocessor.py` (NEW)

**Depends on:** none
**Blocks:** V6 (orchestrator)

**Instructions:**
Create `postprocessor.py` with:
- `ProcessedChunk` dataclass: content, frame_index, timestamp_sec, timestamp_str, source_file, frame_type, content_hash
- `build_chunk(text, frame, frame_type, source_file) -> ProcessedChunk`
  - content_hash = `hashlib.sha256(text.encode()).hexdigest()[:16]`
- `deduplicate_chunks(chunks, similarity_threshold=0.85) -> list[ProcessedChunk]`
  - Sequential comparison: compare each chunk to the previous kept chunk
  - Use character trigram Jaccard similarity
  - Keep chunk if similarity < threshold
- `format_chunk_markdown(chunk) -> str`
  - Returns: `<!-- timestamp: HH:MM:SS | frame: N -->\n{content}`
- `_jaccard(a, b) -> float` and `_ngrams(text, n) -> list[str]` helpers

Import `ExtractedFrame` and `format_timestamp` from `extractor.py` — these are just dataclasses/utils, no heavy deps.

For tests: test dedup with identical strings (should dedup), similar strings (above/below threshold), completely different strings (should keep both). Test hash determinism.

**Definition of Done:**
- [ ] Dedup works correctly at various thresholds
- [ ] Content hash is deterministic
- [ ] Markdown formatting includes timestamp comments
- [ ] Tests pass

---

### Agent E: V5 — Async Job Manager

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/video/jobs.py` (NEW) — Thread-based job manager with progress tracking
- `tests/unit/test_jobs.py` (NEW)

**Depends on:** none
**Blocks:** V9 (MCP tools)

**Instructions:**
Create `jobs.py` with:
- `JobStatus` enum: `QUEUED`, `RUNNING`, `COMPLETE`, `FAILED`
- `JobState` dataclass: job_id (str/UUID), status, progress_pct (int 0-100), current_step (str), result (dict|None), error (str|None), created_at (datetime), updated_at (datetime)
- `JobManager` class:
  - `__init__(max_workers=2, expiry_seconds=3600)`
  - Uses `concurrent.futures.ThreadPoolExecutor`
  - `_jobs: dict[str, JobState]` protected by `threading.Lock`
  - `submit(fn, *args, **kwargs) -> str` — generates UUID job_id, wraps fn to update state on start/complete/fail. The fn must accept a `progress_callback(pct: int, step: str)` as first arg.
  - `get_status(job_id) -> JobState | None`
  - `list_jobs() -> list[JobState]` — returns all non-expired jobs
  - `_cleanup_expired()` — called on list_jobs, removes jobs older than expiry
- Module-level `_manager: JobManager | None = None` with `get_job_manager(max_workers, expiry) -> JobManager` factory (lazy singleton)

Thread safety is critical. All state mutations must be under the lock. The progress_callback updates `progress_pct` and `current_step` atomically.

For tests: submit a fast function, poll until complete. Submit a failing function, verify FAILED state. Test concurrent submissions. Test expiry cleanup.

**Definition of Done:**
- [ ] Jobs execute in background threads
- [ ] Progress callback updates state correctly
- [ ] Thread-safe state access
- [ ] Expiry cleanup works
- [ ] Tests pass (use short timeouts)

---

### Agent F: V7 — YouTube Download Support

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/video/download.py` (NEW) — yt-dlp subprocess wrapper
- `tests/unit/test_download.py` (NEW)

**Depends on:** none
**Blocks:** V9 (MCP tools), V10 (CLI)

**Instructions:**
Create `download.py` with:
- `DownloadResult` dataclass: local_path (Path), title (str), duration_sec (float), url (str)
- `is_url(path_or_url: str) -> bool` — check if string starts with `http://`, `https://`, or `www.`
- `download_video(url: str, output_dir: Path) -> DownloadResult`
  - Use `subprocess.run` with `yt-dlp`:
    ```
    yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
           --merge-output-format mp4
           -o "{output_dir}/%(title)s.%(ext)s"
           --print-json
           {url}
    ```
  - Parse JSON output for title, duration
  - Raise clear error if yt-dlp not found on PATH
  - Return DownloadResult with the local path

For tests: mock subprocess.run to return fake yt-dlp JSON output. Test is_url with various inputs (paths, URLs, edge cases).

**Definition of Done:**
- [ ] Downloads video via yt-dlp subprocess
- [ ] Parses title and duration from yt-dlp JSON
- [ ] `is_url()` correctly distinguishes paths from URLs
- [ ] Graceful error when yt-dlp missing
- [ ] Tests pass with mocked subprocess

---

### Agent G: V8 — VideoConfig Extension

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/video/config.py` (MODIFY) — Add OCR and job config fields
- `configs/base.yaml` (MODIFY) — Add new video config keys
- `tests/unit/test_video_config.py` (NEW)

**Depends on:** none
**Blocks:** V6 (orchestrator), V9 (MCP tools), V10 (CLI)

**Instructions:**
Add these fields to `VideoConfig`:
```python
# OCR settings
vision_model: str = "llava"
scene_threshold: float = 0.3
min_frame_interval: float = 2.0
use_latex_fallback: bool = True
dedup_threshold: float = 0.85
context_window: int = 1
slide_ocr_prompt: str = "..."  # Use the prompt from the starter spec
chalkboard_ocr_prompt: str = "..."  # Use the prompt from the starter spec

# Job settings
max_concurrent_jobs: int = 2
job_expiry_seconds: int = 3600
```

Update `from_dict()` to read all new fields from `video_data`. Use the existing pattern — `video_data.get("field_name", default)`.

Add to `configs/base.yaml` under the existing `video:` section:
```yaml
video:
  # ... existing fields ...
  vision_model: llava
  scene_threshold: 0.3
  min_frame_interval: 2.0
  use_latex_fallback: true
  dedup_threshold: 0.85
  context_window: 1
  max_concurrent_jobs: 2
```

For tests: create a config dict with all fields, verify `from_dict()` round-trips correctly. Test defaults when fields are missing.

**IMPORTANT:** Read the current `configs/base.yaml` before modifying — the `video:` section must remain a top-level key (not nested under `telemetry:`). The `clean_prompt` must keep its `{transcript}` placeholder.

**Definition of Done:**
- [ ] All new config fields with sensible defaults
- [ ] `from_dict()` reads new fields
- [ ] `configs/base.yaml` updated (preserving existing fields)
- [ ] Tests pass
