# Security Audit Report — Plan 23: Fast CLI Help + Audio Queue

**Date:** 2026-09-09
**Auditor:** Grok (automated)
**Scope:** Commits `91de5a2` (CLI help) and `ca996f7` (queued audio transcription) on `plan-23/sprint-1`, vs `docs/plans/plan_23/`. OCR ingest, yt-dlp, and pre-plan-14 pipeline issues are out of scope except where this work re-exposes them.
**Methodology:** Manual review of every new/modified source file against OWASP Top 10, subprocess injection, path traversal, resource exhaustion, and the Plan 23 recorded decisions (R1–R7) plus task DoD.

---

## Executive Summary

The implementation is **substantially complete** for both features. Help no longer imports Chroma/torch/Whisper; transcription extracts audio with list-argv ffmpeg; the queue serializes Whisper and the LLM on separate locks. No hardcoded secrets. ffmpeg is not invoked through a shell.

The most serious issues in *this* diff are **unexpected writes into the source lecture tree** (tree-mode output), **unbounded `--workers` / ffmpeg with no timeout**, and **`extract_audio` not confining the output path** (the plan required that check; it is missing). None of these is remote RCE. This is a local CLI; impact is data loss, disk/CPU/GPU exhaustion, and overwrite of files the user did not ask to touch.

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 1 |
| Medium   | 5 |
| Low      | 4 |

Plan execution: **10 of 12 tasks met their DoD.** The two real misses are path confinement in `extract_audio` (B1/R6) and tree-mode output location (C3: writes next to the MP4s instead of under `scratch` / `output_dir`).

---

## High Severity

### H1 — Tree-mode transcription writes into the source media directories

**Severity:** High
**Files:** `src/tools/video/cli.py` (`transcribe` ~L235, `pipeline` ~L370)
**Description:**
For a nested course tree, combined transcripts are written **into each lecture folder**:

```python
output_path = parent / "transcript.md"          # transcribe, tree mode
scratch = parent                                # pipeline, tree mode
raw_transcript = scratch / "transcript_raw.md"
cleaned_path = scratch / "transcript_cleaned.md"
```

Plan C3 required:

- pipeline: `scratch/<folder>/transcript_raw.md` (one pair **per parent**, under configured scratch)
- transcribe: `output_dir / <parent.name> / transcript.md`

The tests **encode the deviation** (`test_transcribe_tree_writes_per_parent` asserts `p1 / "transcript.md"`).

**Exploit / impact:** `corpus tools video pipeline ./CS6300_Lectures` walks every `P1L*` folder and writes/overwrites `transcript_raw.md` / `transcript_cleaned.md` beside the MP4s. A pre-existing `transcript.md` in that folder is destroyed without confirmation. Those directories are often a read-only dump or a synced drive; this mixes generated artifacts into source, and a second run can clobber hand-edits. Combined with recursive default, one command mutates the entire course tree.

**Remediation:**
Write tree outputs under configured dirs, using the parent folder **name** as a namespace, never the source path:

```python
safe_name = parent.name.replace("..", "_")
output_path = cfg.paths.output_dir / safe_name / "transcript.md"
# pipeline:
scratch = cfg.paths.scratch_dir / "video" / safe_name
```

Refuse to write if `output_path.resolve()` is not under `output_dir` / `scratch_dir` (`utils.security.validate_file_path`). Update the tests that currently require in-tree writes.

---

## Medium Severity

### M1 — `extract_audio` overwrites any path (`-y`) with no confinement

**Severity:** Medium
**File:** `src/tools/video/audio.py`
**Description:**
Plan B1/R6: “Refuse to overwrite outside the intended output path via Path resolution.” Not implemented. The helper:

1. `Path(output_wav).resolve()` then `wav.parent.mkdir(parents=True, exist_ok=True)`
2. Runs `ffmpeg -y ... str(wav)` — **`-y` means overwrite without asking**
3. Never checks that `wav` is under `scratch_dir` (or any allow-list)

`transcribe_file` currently builds `scratch_dir / "audio" / f"{stem}_{uuid}.wav"`. `Path.stem` is usually safe, but the helper is a public function; any caller (MCP, future CLI, a bad config `scratch_dir`) can point ffmpeg at an arbitrary file. `mkdir(parents=True)` will create directories outside the project.

ffmpeg argv is a list (no shell) and `channels` / `sample_rate` go through `int()` — command injection is **not** the issue; unconstrained overwrite is.

**Remediation:**

```python
def extract_audio(video_path, output_wav, *, sample_rate=16000, channels=1, allowed_root: Path | None = None) -> Path:
    wav = Path(output_wav).resolve()
    root = (allowed_root or wav.parent).resolve()
    wav.relative_to(root)  # raises ValueError on escape
    sample_rate = max(8000, min(int(sample_rate), 48000))
    channels = max(1, min(int(channels), 2))
    # then ffmpeg, with timeout=
```

Have `transcribe_file` pass `allowed_root=audio_dir.resolve()`. Prefer `utils.security.validate_file_path`.

---

### M2 — Unbounded `--workers` thread pool

**Severity:** Medium
**Files:** `src/tools/video/cli.py`, `src/tools/video/pipeline_queue.py`
**Description:**
`--workers` is `type=int` with no upper bound. `_default_workers` only clamps the **default** to `>= 1`. The queue only clamps `max_workers < 1` up to 1:

```python
if max_workers < 1:
    max_workers = 1
with ThreadPoolExecutor(max_workers=max_workers) as executor:
```

`corpus tools video transcribe ./Lectures --workers 50000` will try to spawn tens of thousands of threads and run that many concurrent ffmpeg processes (audio extract is **not** gated). Disk, CPU, and RAM exhaustion on a machine that just downloaded the CLI.

`process_course` does not pass `max_workers` at all, so it always uses the function default `2` and **ignores** `video.max_concurrent_jobs` if the user raised it. That is the opposite failure (config ignored), not a DoS.

**Remediation:**
Clamp in one place:

```python
MAX_WORKERS = 8
workers = max(1, min(int(workers), MAX_WORKERS))
```

Apply in the CLI and in `run_transcription_queue`. Cap ffmpeg concurrency separately if workers stay > 2 (audio extract is the unbounded part).

---

### M3 — Recursive discovery follows symlinks and has no size cap

**Severity:** Medium
**File:** `src/tools/video/discover.py`
**Description:**
Default is `recursive=True` (`rglob("*")`). pathlib directory iteration follows symlinks. A lecture folder containing a symlink to `/` or `D:\` will:

- Walk the filesystem (DoS, minutes of stat())
- Queue every matching `.mp4` the process can see (then M2/M4 apply)

Excluded names are only `scratch`, `.git`, `__pycache__`. No cap on file count. No check that `p.resolve()` stays under `root.resolve()`.

**Remediation:**

```python
root_resolved = root.resolve()
if p.is_symlink():
    continue
try:
    p.resolve().relative_to(root_resolved)
except ValueError:
    continue
if len(matches) >= MAX_FILES:  # e.g. 500
    raise RuntimeError(...)
```

Document `--no-recursive` as the safe default for untrusted trees, or keep recursive default but skip symlinks.

---

### M4 — ffmpeg has no timeout

**Severity:** Medium
**File:** `src/tools/video/audio.py`
**Description:**
`subprocess.run(argv, capture_output=True, text=True)` has **no `timeout`**. `utils.security.safe_subprocess_run` defaults to 30s and is unused. A crafted or corrupt MP4 can hang ffmpeg forever and pin a worker (and, with M2, many workers). Long real lectures need a *high* timeout (tens of minutes), not none.

**Remediation:**
`subprocess.run(..., timeout=audio_timeout_seconds)` with a config default of e.g. 1800. On `TimeoutExpired`, kill ffmpeg and fail that job only (the queue already isolates per-file errors).

---

### M5 — Whisper model load is not under the whisper lock

**Severity:** Medium
**File:** `src/tools/video/transcribe.py` (`_load_model` / `transcribe_file`)
**Description:**
Audio extract is intentionally unlocked. Then:

```python
model = self._load_model()   # check-then-act, no lock
with self._gates.whisper:
    segments, _ = model.transcribe(...)
```

`_load_model` is:

```python
if self._model is None:
    self._model = WhisperModel(...)
```

Two workers can both see `_model is None` and both load large-v2 onto the GPU. That is a VRAM OOM / process crash, which the mutex was meant to prevent. Thread-safety of concurrent `WhisperModel()` construction is also undefined.

**Remediation:**
Take `gates.whisper` around load + transcribe, **or** a dedicated `threading.Lock` for initialization:

```python
with self._load_lock:
    model = self._load_model()
with self._gates.whisper:
    ...
```

Keep ffmpeg extract outside both locks.

---

## Low Severity

### L1 — ffmpeg stderr (paths, local filenames) echoed to the user

**Severity:** Low
**File:** `src/tools/video/audio.py` (stderr[:500] in `RuntimeError`); `src/tools/video/cli.py` `_report_results`
**Description:**
Job errors are printed as `✗ {filename}: {result.error}`. ffmpeg often includes absolute paths. Fine for a local CLI; noisy if logs are shared.

**Remediation:** Log full stderr at DEBUG; user-facing message: `ffmpeg failed (exit N)` plus the input **name** only.

### L2 — Unclamped `audio_sample_rate` / `audio_channels` from YAML

**Severity:** Low
**File:** `src/tools/video/config.py`
**Description:**
`from_dict` takes YAML values as-is. `audio_sample_rate: 2147483647` or `audio_channels: 64` makes ffmpeg try to write a huge WAV under scratch.

**Remediation:** Clamp as in M1 (8–48 kHz, 1–2 channels) in `extract_audio` and/or `from_dict`.

### L3 — `clean_prompt.format(transcript=...)` breaks or injects on `{` in the transcript

**Severity:** Low
**File:** `src/tools/video/clean.py`
**Description:**
Whisper output containing `{foo}` raises `KeyError` (job marked failed). `{transcript}` inside the speech would be interpolated. Prompt injection into the local cleaner model is inherent to this feature; the format-string issue is the extra footgun.

**Remediation:** `prompt = self.config.clean_prompt.replace("{transcript}", transcript)` or `string.Template`.

### L4 — `process_course` drops failed files with no error

**Severity:** Low
**File:** `src/orchestrations/lecture_pipeline.py`
**Description:**
Failed queue jobs are filtered out (`r.error is None`). The method returns only successes. A course run can silently skip lectures. The video CLI correctly exits 1.

**Remediation:** Attach skipped sources to the return value or raise/log a summary if `any(r.error)`.

---

## What was done well

- ffmpeg is **list-argv, no shell**; `-vn` / `-map 0:a:0`; `int()` on rate and channels.
- `LazyGroup.format_commands` does not import subcommands; CLI modules defer Chroma/Textual/Whisper.
- Help hygiene tests run in a **subprocess** with a real module blacklist.
- Queue isolates per-file failures; Whisper and LLM use **separate** locks so they can overlap; `locks_internally` avoids deadlock on the real classes.
- WAV files are unique (`uuid4().hex[:8]`) and deleted in `finally` unless `keep_extracted_audio`.
- OCR ingest path (`extract_keyframes`, `ingest`, `ingest-url`) was not rewritten.
- Lecture-pipeline CLI stayed single-file (R7).
- Same-GPU OOM is documented (`--workers 1` / `whisper_device: cpu`).

Pre-existing findings from `docs/audits/security_audit_001.md` (yt-dlp path traversal, `scene_threshold` filter string) are **unchanged** by this work; they still apply to `ingest-url` / OCR.

---

## Plan execution review

Compared to `docs/plans/plan_23/OVERVIEW.md` and the sprint DoDs. Commits: `91de5a2`, `ca996f7`.

### Feature 1 — Fast CLI help

| ID | Requirement | Status |
|----|-------------|--------|
| A1 | `LazyGroup` stores `(import_path, short_help)`; `format_commands` does not `_load_lazy` | **Met.** `src/cli_lazy.py`, maps in `cli.py` / `tools/cli.py` / `learning/cli.py`. |
| A2 | Click modules import only `click` (+ pathlib/lazy) at module level | **Met.** `__getattr__` / in-function imports on rag, video, db, collections, orchestrate, generators, handwriting. |
| A3 | `cli_common` / `db` do not import Chroma at import time | **Met.** `load_cli_db` imports inside the function; `db.__getattr__` for `ChromaDBBackend`. |
| A4 | Subprocess help tests; banned modules absent | **Met.** `tests/unit/test_cli_startup.py` covers the four help paths. Extra: `test_cli_lazy.py`, `test_db_lazy_import.py`. |
| R1 | Help must not import | **Met** (with A2/A3). |
| R2 | Thin CLI modules | **Met.** |

### Feature 2 — Audio extract + queue

| ID | Requirement | Status |
|----|-------------|--------|
| B1 | `extract_audio`, list-argv, `-vn`, mocked tests, missing-ffmpeg error | **Mostly met.** Confinement of `output_wav` (**R6**) is **missing**. No timeout. |
| B2 | `transcribe_file` extracts WAV, Whisper on WAV, delete unless keep flag; config fields | **Met.** `tests/unit/test_transcribe_audio.py`. |
| B3 | YAML + configuration docs for audio keys; transcribe vs OCR | **Met.** |
| C1 | Recursive discover, skip scratch/.git/__pycache__, sorted, FileNotFoundError shape | **Met.** Symlinks not addressed (not in the plan). |
| C2 | `ModelGates`, queue, overlap tests, failure isolation, `skip_clean`, inject gates | **Met.** `locks_internally` is a sound extra. Model **load** not gated (M5). |
| C3 | CLI discover + queue, `--no-recursive`, `--workers`, per-parent combine, exit 1 on partial fail | **Deviated on output path (H1).** Flags, queue, exit 1, single-folder legacy path: met. |
| C4 | `process_course` uses discover + queue; generators after drain; no new orchestrate CLI | **Met**, with two nits: does not pass `max_workers=cfg.max_concurrent_jobs`; failed files dropped (L4). |
| C5 | Docs for recursive, workers, mutexes, per-parent combine, GPU OOM | **Met.** |
| R3 | Audio-only on transcribe; OCR untouched | **Met.** |
| R4 | One job per file; combine per parent | **Met** (combine yes; write location wrong). |
| R5 | Two mutexes, shared model instances, extract unlocked | **Met** except load race (M5). |
| R6 | List-argv ffmpeg; confine output path | **Half.** List-argv yes; confine no. |
| R7 | lecture-pipeline CLI stays single-file | **Met.** |

### Explicit non-goals (correctly left alone)

- torch / faster-whisper extras split
- OCR ingest / `JobManager` rewrite
- GPU VRAM scheduler
- New top-level / `process_course` CLI
- MCP tool list (audio extract is picked up via `transcribe_file`)

### Extra work (not in the plan, fine)

- `__getattr__` on CLI modules so `patch("tools.video.cli.VideoTranscriber")` still works
- `locks_internally` protocol to avoid double-locking
- `tests/unit/test_cli_lazy.py`, `test_db_lazy_import.py`, `test_transcribe_audio.py`

### Leftover API

`VideoTranscriber.transcribe_folder` still uses shallow `iterdir()` and does not go through the queue. The CLI no longer calls it. Harmless but two discovery implementations now exist.

---

## Priority fixes

1. **H1** — Stop writing transcripts into the media tree; use `scratch_dir` / `output_dir`.
2. **M1** — Confine `extract_audio` output; clamp rate/channels.
3. **M2** — Cap `--workers` (and ffmpeg fan-out).
4. **M5** — Lock Whisper **load**.
5. **M4** — ffmpeg timeout.
6. **M3** — Skip symlinks; cap discovered files.

---

## Appendix — files reviewed

New: `src/tools/video/audio.py`, `discover.py`, `pipeline_queue.py`; tests `test_audio.py`, `test_discover.py`, `test_pipeline_queue.py`, `test_cli_startup.py`, `test_cli_lazy.py`, `test_db_lazy_import.py`, `test_transcribe_audio.py`.

Modified (security-relevant): `transcribe.py`, `clean.py`, `cli.py` (video), `config.py`, `lecture_pipeline.py`, `cli_lazy.py`, `cli_common.py`, `db/__init__.py`.
