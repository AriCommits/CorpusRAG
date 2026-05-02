# Sprint 4 — Dependencies & Documentation

**Plan:** docs/plans/plan_14/OVERVIEW.md
**Wave:** 4 of 4
**Can run in parallel with:** none — final wave
**Must complete before:** nothing — this is the last wave

---

## Agents in This Wave

### Agent A: V11 — Dependencies & Documentation

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `pyproject.toml` (MODIFY) — Add video OCR dependencies
- `README.md` (MODIFY) — Update video section
- `src/CLI.md` (MODIFY) — Document new video commands
- `src/mcp_server/README.md` (MODIFY) — Document new MCP video tools

**Depends on:** V9 (MCP tools), V10 (CLI)
**Blocks:** none

**Instructions:**

**pyproject.toml:**
Update the `video` extra dependencies:
```toml
video = [
    "faster-whisper>=1.0.0",
    "Pillow>=10.0.0",
    "numpy>=1.24.0",
]
```
pix2tex is optional (not in deps — users install manually if they want math OCR). Document this.

Note: `yt-dlp` and `ffmpeg` are system tools, not Python packages. Document as system requirements.

**README.md:**
Update the feature table to mention visual OCR and combined pipeline. Update the video row:
```
| **Video** | Transcribe lectures with Whisper, extract slide/chalkboard text with vision OCR, auto-ingest |
```

Add a "Video Pipeline" section under Documentation or expand the existing Quick Start to show:
```bash
corpus video ingest lecture.mp4 -c cs6301
corpus video ingest-url "https://youtube.com/watch?v=..." -c ocw_mit
corpus video ingest lecture.mp4 -c cs6301 --combined  # audio + visual
```

**src/CLI.md:**
Document all new commands:
- `corpus video ingest` with all options
- `corpus video ingest-url` with all options
- `corpus video jobs`
- `corpus video status <job_id>`

**src/mcp_server/README.md:**
Document the 5 new MCP tools:
- `video_ingest_local` — params, return shape, async behavior
- `video_ingest_url` — params, return shape
- `video_combined_pipeline` — params, what it does, merge behavior
- `video_job_status` — params, return shape
- `video_list_jobs` — return shape

Include example MCP tool calls and expected responses.

**Definition of Done:**
- [ ] pyproject.toml has correct video deps
- [ ] README reflects new video capabilities
- [ ] CLI.md documents all new commands with examples
- [ ] MCP README documents all 5 new tools with examples
- [ ] System requirements (ffmpeg, yt-dlp) documented
