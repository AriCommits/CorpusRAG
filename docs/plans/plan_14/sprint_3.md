# Sprint 3 — MCP Tools & CLI Integration

**Plan:** docs/plans/plan_14/OVERVIEW.md
**Wave:** 3 of 4
**Can run in parallel with:** Agent A and Agent B can run in parallel (no file conflicts)
**Must complete before:** Sprint 4

---

## Agents in This Wave

### Agent A: V9 — MCP Video Tools

**Complexity:** L
**Estimated time:** 3 hours
**Files to modify:**
- `src/mcp_server/tools/video.py` (NEW) — MCP tool implementations
- `src/mcp_server/profiles.py` (MODIFY) — Register video tools
- `tests/unit/test_mcp_video.py` (NEW)

**Depends on:** V5 (jobs), V6 (orchestrator), V7 (download), V8 (config)
**Blocks:** V11 (docs)

**Instructions:**
Create `src/mcp_server/tools/video.py` with 5 tool implementation functions (pure logic, no decorators — those go in profiles.py):

**1. `video_ingest_local(path, collection, config, db, job_manager, **opts) -> dict`**
- Validate path exists, is a supported video extension
- Submit `ingest_video()` to job_manager with progress callback
- Return `{"status": "submitted", "job_id": "...", "message": "..."}`

**2. `video_ingest_url(url, collection, config, db, job_manager, **opts) -> dict`**
- Submit a wrapper function that: downloads via `download_video()`, then runs `ingest_video()` on the result
- Progress: download = 0-10%, OCR pipeline = 10-100% (scaled)
- Return `{"status": "submitted", "job_id": "..."}`

**3. `video_combined_pipeline(path_or_url, collection, config, db, job_manager, include_audio=True, include_visual=True) -> dict`**
- This is the key tool. Submit a wrapper that:
  - If URL, download first
  - Run Whisper transcription (existing `VideoTranscriber`) and visual OCR (`ingest_video`) concurrently using `concurrent.futures.ThreadPoolExecutor(max_workers=2)` inside the job
  - Merge results by timestamp: for each visual chunk, find the nearest audio segment by timestamp and append it
  - Merged format per chunk:
    ```
    <!-- timestamp: HH:MM:SS | frame: N | type: slide -->
    [Visual content from OCR]

    **Audio transcript:**
    [Whisper transcript for this time range]
    ```
  - Ingest merged chunks into ChromaDB with `source_type: "video_combined"`
- Return `{"status": "submitted", "job_id": "..."}`

**4. `video_job_status(job_id, job_manager) -> dict`**
- Call `job_manager.get_status(job_id)`
- Return full state as dict: status, progress_pct, current_step, result, error

**5. `video_list_jobs(job_manager) -> dict`**
- Return all jobs with their states

**Register in `profiles.py`:**
Add a `register_video_tools(mcp, config, db, store)` function. Call it from `register_learn_tools` and ensure it's included in `full` profile too. The video tools need a shared `JobManager` instance — create it in the register function using config values.

Pattern to follow — look at how `register_dev_tools` wraps tool functions with `@mcp.tool()` decorators and telemetry logging. Do the same for video tools.

**For tests:** Mock the job manager, ingest pipeline, and download. Verify each tool returns correct structure. Test combined pipeline merge logic with sample timestamped data.

**Definition of Done:**
- [ ] 5 MCP tools registered and returning correct response shapes
- [ ] Async execution via JobManager for ingest tools
- [ ] Combined pipeline merges audio + visual by nearest timestamp
- [ ] Tools registered in learn and full profiles
- [ ] Telemetry logging on each tool call
- [ ] Unit tests pass

---

### Agent B: V10 — CLI Integration

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/video/cli.py` (MODIFY) — Add ingest, ingest-url, jobs, status commands
- `tests/unit/test_video_cli.py` (NEW)

**Depends on:** V6 (orchestrator), V7 (download), V8 (config)
**Blocks:** V11 (docs)

**Instructions:**
Add new commands to the existing `video` click group in `src/tools/video/cli.py`. Keep existing commands (transcribe, clean, augment, pipeline) untouched.

**`corpus video ingest <path> -c <collection>`**
```python
@video.command("ingest")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("--collection", "-c", required=True)
@click.option("--threshold", default=None, type=float, help="Scene detection sensitivity (0.0-1.0)")
@click.option("--model", default=None, help="Ollama vision model")
@click.option("--no-latex", is_flag=True)
@click.option("--context-window", default=None, type=int)
@click.option("--keep-frames", is_flag=True)
@click.option("--combined", is_flag=True, help="Also run Whisper and merge audio+visual")
@click.option("--config", "-f", default="configs/base.yaml")
```
- Load config, build overrides dict from non-None options
- If `--combined`: run both Whisper + OCR, merge by timestamp (reuse logic from MCP combined pipeline, but synchronous)
- Else: run visual OCR pipeline only
- Show click.progressbar during processing using the progress_cb
- Print summary at end

**`corpus video ingest-url <url> -c <collection>`**
- Same options as ingest
- First download via `download_video()`, then run ingest on the result
- Show download progress, then processing progress

**`corpus video jobs`**
- List all active/recent jobs from JobManager
- Table format: job_id (short), status, progress, step, created_at

**`corpus video status <job_id>`**
- Show detailed status for a specific job

**IMPORTANT:** Use lazy imports for all new dependencies. The existing video CLI already imports `TranscriptCleaner`, `TranscriptAugmenter`, `VideoTranscriber`, `VideoConfig` at module level. These are lightweight. The new ingest/download imports should go inside the command functions to keep `corpus video --help` fast.

**For tests:** Use click.testing.CliRunner to test argument parsing and help text. Mock the actual pipeline execution.

**Definition of Done:**
- [ ] `corpus video ingest` works with progress bar
- [ ] `corpus video ingest-url` downloads then ingests
- [ ] `corpus video jobs` and `corpus video status` show job info
- [ ] `--combined` flag merges audio + visual
- [ ] Lazy imports — `corpus video --help` stays fast
- [ ] Tests pass
