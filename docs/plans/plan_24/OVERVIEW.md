# Plan 24: Close Plan-23 Audit Findings

## Summary

Plan 23 shipped fast CLI help and the audio transcription queue. The follow-up
audit (`docs/audits/security_audit_002.md`) found no RCE or secrets, but
tree-mode pipeline/transcribe **write markdown into the source lecture
folders**, `extract_audio` will `ffmpeg -y` any path with no confinement or
timeout, `--workers` and recursive `rglob` are unbounded, and Whisper **load**
is outside the whisper lock. This plan applies those remediations: generated
transcripts land under configured `output_dir` / `scratch_dir`, ffmpeg is
path-confined and timed out, workers and discovery are capped, model load is
serialized, and the low-severity clean/error/`process_course` gaps are closed.

End state: `corpus tools video pipeline ./Course` never creates
`Course/P1L1/transcript_raw.md`. WAV files cannot escape `scratch/audio`.
`--workers 50000` is rejected. Two queue workers cannot both construct
`WhisperModel`. Failed course jobs are reported.

## Goals

- Nested `transcribe` / `pipeline` writes go under `paths.output_dir` and
  `paths.scratch_dir`, namespaced by path relative to the input root. Source
  media directories are not modified.
- `extract_audio` refuses to write outside an allowed root, clamps sample
  rate/channels, and times out ffmpeg.
- `run_transcription_queue` and the CLI clamp workers to `[1, 8]`.
- `discover_media_files` skips symlinks, requires resolved paths to stay
  under the root, and errors if more than a fixed file cap is found.
- `VideoTranscriber._load_model` is serialized so two workers cannot both
  load weights.
- `process_course` honors `max_concurrent_jobs` (clamped) and surfaces
  per-file queue failures.
- Cleaner prompt interpolation does not use `str.format` on the transcript.
- User-facing ffmpeg errors do not dump raw stderr paths.
- Tests cover the new guards; existing queue/CLI/discover/transcribe tests
  are updated for the new output locations.

## Non-Goals

- Do not re-open plan-14 OCR issues (yt-dlp filenames, `scene_threshold`
  filter injection). Those remain on `ingest` / `ingest-url`.
- Do not add a GPU VRAM scheduler or a third `gpu` lock.
- Do not change CLI help laziness, extras packaging, or MCP tool lists.
- Do not add a `process_course` CLI (plan 23 R7 still holds).
- Do not persist the job queue or rewrite `JobManager`.

## Background / Context

Branch: `plan-24/dev` off `plan-23/sprint-1` (`ca996f7`). Source of findings:
`docs/audits/security_audit_002.md` (H1, M1–M5, L1–L4).

Plan 23 C3 required tree outputs under scratch/output; the implementation
(and `test_transcribe_tree_writes_per_parent`) wrote `parent / "transcript.md"`
instead. This plan treats that as a bug, not a feature: tests change.

`utils.security.validate_file_path` already exists for allow-listed roots.
Prefer it (or `Path.relative_to`) over a new helper unless the existing
API is too awkward for a not-yet-created WAV.

### Recorded decisions

- **R1 — Tree outputs stay in configured dirs:** Relative path from the
  discovery root (`P1L1`, or `week1/P1L1` if nested) under `output_dir`
  (transcribe) or `scratch_dir / "video"` (pipeline). Sanitize `..`.
  Single-folder legacy paths unchanged.
- **R2 — Worker cap is 8:** Constant `MAX_WORKERS = 8` in `pipeline_queue`.
  CLI and `process_course` go through the same clamp. Below 1 becomes 1.
- **R3 — Discovery cap is 500 files:** Constant `MAX_DISCOVERED_FILES = 500`.
  Over the cap raises `RuntimeError` (not silent truncate). Symlinks skipped.
- **R4 — ffmpeg timeout default 1800s:** `VideoConfig.audio_timeout_seconds`.
  `TimeoutExpired` fails that job only.
- **R5 — Whisper load uses the whisper lock:** Take `gates.whisper` around
  `_load_model` + transcribe. ffmpeg extract stays unlocked.

## Features / Tasks

### H1: Stop writing transcripts into source lecture folders
**Files:** `src/tools/video/cli.py` (modify),
`tests/unit/test_video_cli.py` (modify),
`src/tools/video/README.md` (modify),
`src/CLI.md` (modify),
`docs/tools-usage.md` (modify)
**Complexity:** M
**Depends on:** none

Add `_output_subdir(root: Path, parent: Path) -> Path`: relative path of
`parent` under `root`, with `.` / `..` stripped. Fall back to `parent.name`.

- `transcribe` tree mode: `cfg.paths.output_dir / subdir / "transcript.md"`
  (not `parent / "transcript.md"`).
- `pipeline` tree mode: `cfg.paths.scratch_dir / "video" / subdir / ...`
  (not `scratch = parent`).
- After building the path, resolve and `relative_to` the configured root;
  raise `click.ClickException` on escape.
- Single-folder / `--output` / course+lecture legacy paths stay as they are.
- Rewrite `test_transcribe_tree_writes_per_parent` and any pipeline tree
  test to assert configured dirs, and assert the source folder has **no**
  new `transcript*.md`.

### M1: Confine extract_audio output and clamp audio params
**Files:** `src/tools/video/audio.py` (modify),
`src/tools/video/transcribe.py` (modify),
`src/tools/video/config.py` (modify),
`tests/unit/test_audio.py` (modify),
`tests/unit/test_transcribe_audio.py` (modify),
`tests/unit/test_video_config.py` (modify)
**Complexity:** M
**Depends on:** none

`extract_audio(..., *, allowed_root: Path, sample_rate=..., channels=..., timeout=...)`:

- Resolve `output_wav`; require `wav.relative_to(allowed_root.resolve())`.
  Raise `ValueError` (or `PathTraversalError`) on escape. `mkdir` only after
  the check.
- Clamp `sample_rate` to `[8000, 48000]`, `channels` to `[1, 2]`.
- `transcribe_file` passes `allowed_root=audio_dir.resolve()` and creates
  `audio_dir` first.
- Keep list-argv ffmpeg, no shell.

Covers audit M1 and L2.

### M4: ffmpeg timeout
**Files:** `src/tools/video/audio.py` (modify),
`src/tools/video/config.py` (modify),
`configs/base.yaml` (modify),
`configs/base.example.yaml` (modify),
`configs/video.example.yaml` (modify),
`docs/configuration.md` (modify),
`tests/unit/test_audio.py` (modify),
`tests/unit/test_video_config.py` (modify)
**Complexity:** S
**Depends on:** M1

Pass `timeout=config.audio_timeout_seconds` (default **1800**) into
`subprocess.run`. On `TimeoutExpired`, raise `RuntimeError("ffmpeg timed out")`
without dumping the full command line. Wire the config field through
`from_dict` and example YAML.

### M2: Cap queue workers
**Files:** `src/tools/video/pipeline_queue.py` (modify),
`src/tools/video/cli.py` (modify),
`src/orchestrations/lecture_pipeline.py` (modify),
`tests/unit/test_pipeline_queue.py` (modify),
`tests/unit/test_video_cli.py` (modify)
**Complexity:** S
**Depends on:** none

Export `MAX_WORKERS = 8` and `clamp_workers(n) -> int` (`max(1, min(int(n), 8))`).
Call it at the start of `run_transcription_queue` and in `_default_workers` /
CLI `--workers` resolution. `process_course` passes
`max_workers=clamp_workers(self.video_config.max_concurrent_jobs)`.

CLI `--workers 5` still works (test already exists). Add a test that
`--workers 50000` (or passing 50000 into the queue) becomes 8.

### M3: Harden discover_media_files
**Files:** `src/tools/video/discover.py` (modify),
`tests/unit/test_discover.py` (modify)
**Complexity:** M
**Depends on:** none

- Skip files and directories that are symlinks (`p.is_symlink()`).
- After match, `resolved.relative_to(root.resolve())`; skip on `ValueError`.
- If the match list would exceed `MAX_DISCOVERED_FILES = 500`, raise
  `RuntimeError` naming the cap and the root.
- Keep excluded dir names, recursive flag, and empty-dir `FileNotFoundError`.

Tests: symlink to a file outside the tree is not returned; a symlink dir is
not walked; over-cap raises (inject a small cap via patch or a test-only
parameter `max_files=` defaulting to the constant — prefer an optional
`max_files` kwarg defaulting to the constant so the test does not create 501
files).

### M5: Serialize Whisper model load
**Files:** `src/tools/video/transcribe.py` (modify),
`tests/unit/test_transcribe_audio.py` (modify)
**Complexity:** S
**Depends on:** none

Hold `self._gates.whisper` across `_load_model()` **and** `model.transcribe`
iteration. ffmpeg `extract_audio` stays outside the lock. Add a unit test
with a fake gate/lock around `_load_model` if feasible; at minimum assert
(via reading the source or a threading test) that load is not called outside
the lock. A small threading test: two `transcribe_file` calls, `_load_model`
instrumented with a counter of concurrent entries, must stay at 1.

### L1: Short ffmpeg errors
**Files:** `src/tools/video/audio.py` (modify),
`tests/unit/test_audio.py` (modify)
**Complexity:** S
**Depends on:** M1, M4

User-facing `RuntimeError` is `ffmpeg failed (exit N)` or `ffmpeg timed out`.
Log stderr at `logger.debug`. Tests assert the message does not include a
path-looking stderr blob.

### L3: Safe cleaner prompt interpolation
**Files:** `src/tools/video/clean.py` (modify),
`tests/unit/test_pipeline_queue.py` or `tests/unit/test_clean_prompt.py` (new)
**Complexity:** S
**Depends on:** none

Replace `self.config.clean_prompt.format(transcript=transcript)` with a
single `{transcript}` replacement that does not interpret other braces:

```python
prompt = self.config.clean_prompt.replace("{transcript}", transcript)
```

Test: transcript containing `{not_a_field}` still produces a prompt (no
`KeyError`).

### L4: process_course reports queue failures
**Files:** `src/orchestrations/lecture_pipeline.py` (modify),
`tests/unit/test_orchestrations.py` (modify)
**Complexity:** S
**Depends on:** M2

After the queue drains, collect jobs with `error`. Successful jobs still
generate materials. If any failed, raise `RuntimeError` summarizing
`{n} file(s) failed: ...` **after** successes have been processed (or return
results and attach `errors` — prefer raise-after-success so CLI/library
callers cannot miss it). Test: one boom + one success → one result and
exception, or results-plus-errors list. Prefer: return the successful
results list and raise a dedicated `CourseTranscriptionError` that carries
`.results` and `.failures` so callers who catch still have the successes.

Simplest testable contract: return `results` as today for the all-success
path; if any failure, raise `CourseTranscriptionError(results=..., failures=...)`.

## New Dependencies

| Package | Feature | Optional? |
|---|---|---|
| *(none)* | stdlib only | — |

## File Change Summary

| File | Action |
|---|---|
| `src/tools/video/cli.py` | modify |
| `src/tools/video/audio.py` | modify |
| `src/tools/video/discover.py` | modify |
| `src/tools/video/pipeline_queue.py` | modify |
| `src/tools/video/transcribe.py` | modify |
| `src/tools/video/clean.py` | modify |
| `src/tools/video/config.py` | modify |
| `src/tools/video/README.md` | modify |
| `src/orchestrations/lecture_pipeline.py` | modify |
| `src/CLI.md` | modify |
| `docs/tools-usage.md` | modify |
| `docs/configuration.md` | modify |
| `configs/base.yaml` | modify |
| `configs/base.example.yaml` | modify |
| `configs/video.example.yaml` | modify |
| `tests/unit/test_video_cli.py` | modify |
| `tests/unit/test_audio.py` | modify |
| `tests/unit/test_discover.py` | modify |
| `tests/unit/test_pipeline_queue.py` | modify |
| `tests/unit/test_transcribe_audio.py` | modify |
| `tests/unit/test_video_config.py` | modify |
| `tests/unit/test_orchestrations.py` | modify |
| `tests/unit/test_clean_prompt.py` | new |

## Open Questions

- **Collision of parent names:** Relative-to-root (R1) avoids `week1/P1L1` vs
  `week2/P1L1` collapsing. Confirmed; no open choice.
- **Raise vs return on course failures:** Recorded as
  `CourseTranscriptionError` carrying both lists. No further product
  decision needed.
- **500 file cap:** High enough for CS6300-style dumps (hundreds of short
  clips) and low enough to stop a symlink-to-root walk. Revisit only if a
  real course exceeds it.
