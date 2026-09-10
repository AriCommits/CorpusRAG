# Sprint 2 — Audio-only transcription and pipeline queue

**Plan:** docs/plans/plan_23/OVERVIEW.md
**Wave:** 2 of 2 (Feature 2 of 2)
**Can run in parallel with:** Sprint 1, except task **C3** which must wait for Sprint 1 **A2** (`src/tools/video/cli.py`).
**Must complete before:** nothing (final feature)

This sprint is the lecture-transcription feature. Visual OCR ingest (`corpus tools video ingest`, `extract_keyframes`) is frozen. ffmpeg is already required on PATH.

**Phase 1 (parallel):** B1, C1.
**Phase 2 (after B1):** B2.
**Phase 3 (after B2 + C1):** C2. B3 may start after B2 in parallel with C2.
**Phase 4 (after C2):** C4 immediately. C3 after C2 **and** Sprint 1 A2.
**Phase 5 (after C3, C4, B3):** C5.

Branch from `plan-23/dev`. If Sprint 1 is in flight, start B1/C1/B2/C2/C4 on this branch and merge A2 before C3.

---

## Agents in This Wave

### Agent A: B1 — ffmpeg audio extract helper

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/video/audio.py` (NEW)
- `tests/unit/test_audio.py` (NEW)

**Depends on:** none
**Blocks:** B2

**Instructions:**

Do **not** add this to `extractor.py` (OCR keyframes). New module.

```python
def extract_audio(
    video_path: Path,
    output_wav: Path,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    ...
```

ffmpeg argv, **list form, no shell**:

```
ffmpeg -y -nostdin -hide_banner -loglevel error
  -i <video> -vn -map 0:a:0 -ac <channels> -ar <sample_rate>
  -c:a pcm_s16le <output_wav>
```

Rules (plan R3, R6): 
- `output_wav.parent.mkdir(parents=True, exist_ok=True)`.
- The only non-literal argv slots are the two resolved `Path`s and the int `channels` / `sample_rate` (pass as `str(int(...))`).
- `FileNotFoundError` on the binary → `RuntimeError("ffmpeg not found. Install ffmpeg and ensure it is on your PATH.")` — same wording as `extract_keyframes`.
- Non-zero ffmpeg exit → raise `RuntimeError` including a short stderr snippet (no audio stream, corrupt file).
- Return `output_wav`.

Tests mock `subprocess.run`. Do not call a real ffmpeg.

- Happy path: argv contains `-vn`, `-map`, `0:a:0`, `-ac`, `1`, `-ar`, `16000`, `-c:a`, `pcm_s16le`, both paths.
- Missing binary → `RuntimeError` matching `ffmpeg not found`.
- `CompletedProcess` with `returncode=1` → `RuntimeError`.
- Custom `sample_rate=8000`, `channels=2` appear in argv.

**Definition of Done:**
- [ ] `extract_audio` uses list-argv ffmpeg with `-vn`.
- [ ] Missing ffmpeg and non-zero exit are tested.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent B: C1 — Recursive media discovery

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/video/discover.py` (NEW)
- `tests/unit/test_discover.py` (NEW)

**Depends on:** none
**Blocks:** C2

**Instructions:**

```python
def discover_media_files(
    root: Path,
    extensions: Sequence[str],
    *,
    recursive: bool = True,
) -> list[Path]:
```

- File whose suffix (case-insensitive) is in `extensions` → `[root.resolve()]`.
- File with the wrong suffix → `FileNotFoundError` mentioning supported formats.
- Directory + `recursive=True` → `rglob("*")` filtered by suffix.
- Directory + `recursive=False` → `iterdir()` only (today's `transcribe_folder` behavior).
- Skip walking directories named `scratch`, `.git`, `__pycache__`.
- Return `sorted(...)` for a stable order.
- Directory with zero matches → `FileNotFoundError` with the supported-extension list, same shape as `VideoTranscriber.transcribe_folder` today.

No ffmpeg, no Whisper. Tests use `tmp_path`:

- Nested `P1L1/a.mp4` + `P1L2/b.MP4` found when recursive.
- Same tree with `recursive=False` from the parent finds nothing.
- Flat folder still works.
- Empty folder raises.
- Skip a `.git` dir that contains a dummy `.mp4`.

**Definition of Done:**
- [ ] Recursive default finds nested MP4s; `--` equivalent `recursive=False` is shallow.
- [ ] Empty / wrong-suffix cases raise `FileNotFoundError`.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent A: B2 — Transcribe from extracted audio

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/video/transcribe.py` — extract WAV, then Whisper that file
- `src/tools/video/config.py` — audio settings
- `tests/unit/test_video_config.py` — new fields / defaults

**Depends on:** B1
**Blocks:** C2, B3

**Instructions:**

`VideoTranscriber.transcribe_file` today passes the MP4 path to `WhisperModel.transcribe`. Change it to:

1. WAV path = `config.paths.scratch_dir / "audio" / f"{video_path.stem}_{unique}.wav"`. `unique` must not collide across workers (`uuid4().hex[:8]` is enough).
2. `extract_audio(video_path, wav, sample_rate=config.audio_sample_rate, channels=config.audio_channels)`.
3. `model.transcribe(str(wav), language=...)` — same segment formatting as today.
4. `finally`: delete the WAV unless `config.keep_extracted_audio`.

Keep `_load_model` lazy. Do **not** take a mutex here yet (C2 injects `ModelGates`). Do **not** change `transcribe_folder` beyond the fact that it already calls `transcribe_file` (C3 will switch the folder path to the queue). MCP `transcribe_video` and `process_lecture` keep their signatures and pick this up automatically.

`VideoConfig` / `from_dict` / defaults:

- `audio_sample_rate: int = 16000`
- `audio_channels: int = 1`
- `keep_extracted_audio: bool = False`

OCR fields stay. Extend `tests/unit/test_video_config.py` for defaults and overrides.

Unit-test `transcribe_file` with mocks: patch `extract_audio` and `_load_model`; assert Whisper is called with the WAV path, not the MP4; assert the WAV is unlinked when `keep_extracted_audio` is false. Add this to `tests/unit/test_audio.py` or a small `tests/unit/test_transcribe.py` (new is fine).

**Definition of Done:**
- [ ] `transcribe_file` never hands the MP4 to Whisper; it hands the extracted WAV.
- [ ] WAV deleted after success unless `keep_extracted_audio`.
- [ ] Config fields default 16000 / 1 / false.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent A: C2 — Model mutexes and transcription queue

**Complexity:** L
**Estimated time:** 4 hours
**Files to modify:**
- `src/tools/video/pipeline_queue.py` (NEW)
- `tests/unit/test_pipeline_queue.py` (NEW)
- `src/tools/video/transcribe.py` — optional injectable `ModelGates` around the Whisper call
- `src/tools/video/clean.py` — optional injectable `ModelGates` around `clean` / `clean_file`

**Depends on:** C1, B2
**Blocks:** C3, C4

**Instructions:**

New module. Do **not** use `tools.video.jobs.JobManager`.

Types:

- `ModelGates`: two `threading.Lock`s, `whisper` and `llm`, usable as context managers (`with gates.whisper:`, `with gates.llm:`). Default constructable.
- `TranscriptJobResult`: `source: Path`, `parent: Path`, `raw: str | None`, `cleaned: str | None`, `error: str | None`.
- `run_transcription_queue(files, *, transcriber, cleaner=None, skip_clean=False, max_workers=2, gates=None) -> list[TranscriptJobResult]`

Worker per file:

1. `transcriber.transcribe_file(path)` under `gates.whisper` (if the transcriber does not lock internally).
2. If not `skip_clean` and `cleaner` is set: `cleaner.clean(raw)` under `gates.llm`.
3. On exception: set `error=str(e)`, leave text None, **do not** abort siblings.
4. Return all results (including failures). CLI (C3) exits 1. Do not raise a combined error from the queue function.

Prefer **injecting `ModelGates` into `VideoTranscriber` and `TranscriptCleaner`** (`__init__(..., gates: ModelGates | None = None)` stored as `self._gates` defaulting to a process-local singleton or a new `ModelGates()`). Then `transcribe_file` wraps only the `model.transcribe(...)` call (not ffmpeg extract) with `whisper`; `clean` wraps the LLM complete with `llm`. Audio extract stays unlocked so it overlaps Whisper.

Share **one** transcriber and **one** cleaner across workers (one Whisper weight load). `ThreadPoolExecutor(max_workers)`. `max_workers=1` is valid.

Discovery is **not** this task; the caller passes `files`. You may import `discover_media_files` only in tests.

Tests — no real models, fake transcriber/cleaner with `time.sleep` + timestamp logs:

- Two jobs: clean of job A overlaps transcribe of job B (different locks).
- Two threads cannot be inside the whisper lock at the same time (Event/barrier).
- Three files, middle raises: two successes, one `error`.
- `skip_clean=True` never calls cleaner.

**Definition of Done:**
- [ ] Queue overlaps Whisper and LLM across files; Whisper is exclusive; LLM is exclusive.
- [ ] One failure does not drop sibling results.
- [ ] `skip_clean` skips cleaner.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent C: B3 — Audio-extract config docs

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `configs/base.yaml`
- `configs/base.example.yaml`
- `configs/video.example.yaml`
- `docs/configuration.md`
- `src/tools/video/README.md`

**Depends on:** B2
**Blocks:** C5 (same docs files)

**Instructions:**

Document `audio_sample_rate`, `audio_channels`, `keep_extracted_audio` next to the existing Whisper settings. State that **transcription** demuxes audio only (`ffmpeg -vn`) and that **`corpus tools video ingest` is the OCR path that still reads frames**. `keep_extracted_audio` is a debug flag (WAVs land under `paths.scratch_dir / audio`). ffmpeg must be on PATH.

Do **not** document `--workers`, recursive discovery, or the queue yet (C5). If you touch `README.md` / `configuration.md`, leave those sections for C5 or add a one-line stub C5 will expand.

Keep YAML comments in the same style as the surrounding `video:` block.

**Definition of Done:**
- [ ] Example YAMLs include the three new keys with defaults 16000 / 1 / false.
- [ ] Docs distinguish transcribe (audio) vs ingest (OCR).
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent A: C3 — Wire video CLI transcribe + pipeline to the queue

**Complexity:** M
**Estimated time:** 2.5 hours
**Files to modify:**
- `src/tools/video/cli.py` — `transcribe` and `pipeline` only
- `src/tools/video/transcribe.py` — `transcribe_folder` / `combine_transcripts` as needed
- `src/tools/video/config.py` — only if a `recursive` field is required; prefer a CLI flag
- `tests/unit/test_video_cli.py`

**Depends on:** C2, A2
**Blocks:** C5

**Instructions:**

**Stop if Sprint 1 A2 is not merged.** A2 only moved imports in this file. Rebase/merge it, then change behavior.

`transcribe` and `pipeline`:

1. `discover_media_files(Path(input_folder), cfg.supported_extensions, recursive=not no_recursive)`.
2. Echo `Queued N videos…` **before** constructing `VideoTranscriber` (no Whisper load for an empty wait).
3. `run_transcription_queue(..., skip_clean=pipeline's skip_clean / not transcribe's --clean, max_workers=workers or cfg.max_concurrent_jobs)`.
4. Group successful results by `parent`. `combine_transcripts` per group. Keep `## Segment i: filename`.
   - `pipeline`: today's `scratch/<folder>/transcript_raw.md` (+ cleaned) when the input is a single folder; **one pair per parent folder** when the input is a tree (`scratch/<parent.name>/...`).
   - `transcribe`: today's output path for a single folder; for a tree, `output_dir / <parent.name> / transcript.md`.
5. Print per-file success/fail. Exit 1 if any `error`.

Flags: `--no-recursive` (shallow `iterdir`), `--workers` (default `cfg.max_concurrent_jobs`). `pipeline --augment` stays serial on each combined file after the queue drains.

OCR commands (`ingest`, `ingest-url`, `jobs`, `status`) stay as A2 left them. Keep imports inside command bodies (A2 contract) so help tests keep passing.

Tests: mock discover + queue; assert `--help` still lists `transcribe` / `pipeline`; assert a nested tmp tree is queued as multiple jobs; assert `--no-recursive` is passed through.

**Definition of Done:**
- [ ] Directory inputs are queued recursively by default.
- [ ] Combine is per parent directory.
- [ ] `--no-recursive` and `--workers` exist on `transcribe` and `pipeline`.
- [ ] Partial failures exit 1 without dropping successful outputs.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent B: C4 — Lecture `process_course` uses the same queue

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/orchestrations/lecture_pipeline.py`
- `tests/test_lecture_pipeline_config.py`
- `tests/unit/test_orchestrations.py`

**Depends on:** C2
**Blocks:** C5

**Instructions:**

Do **not** add orchestrate CLI flags (plan R7). `corpus orchestrate lecture-pipeline` stays single-file.

`process_course(video_folder, ...)`:

1. `discover_media_files(video_folder, self.video_config.supported_extensions, recursive=True)`.
2. One shared `VideoTranscriber` + `TranscriptCleaner` + `ModelGates`.
3. `run_transcription_queue` for transcribe+clean (`skip_clean` from the existing resolve path).
4. **Wait for the queue to drain.** Then, for each successful file in sorted order, run ingest / summary / flashcards / quiz exactly as `process_lecture` does today. Do not overlap generators with Whisper.

Keep `process_lecture` (single file). It already gets audio extract via B2. It does not need the executor.

Replace the hardcoded `video_extensions = [".mp4", ...]` list with `self.video_config.supported_extensions`.

Tests: mock transcriber/cleaner/queue or patch `discover_media_files` + `run_transcription_queue`. Nested tmp tree (`P1L1/a.mp4`, `P1L2/b.mp4`) must produce two transcribe calls. Existing `process_lecture` tests stay green (`transcribe_file` still one positional path).

**Definition of Done:**
- [ ] `process_course` sees nested files and queues transcribe+clean.
- [ ] Generators run after the queue, still per file.
- [ ] `process_lecture` signatures and tests unchanged.
- [ ] No new orchestrate CLI.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests

---

### Agent C: C5 — Queue / discovery docs

**Complexity:** S
**Estimated time:** 1.5 hours
**Files to modify:**
- `src/tools/video/README.md`
- `src/CLI.md`
- `docs/tools-usage.md`
- `docs/configuration.md`

**Depends on:** C3, C4, B3
**Blocks:** none

**Instructions:**

Land **after** B3 so you extend the audio docs rather than racing `configuration.md` / `README.md`.

Document:

- Recursive discovery (default) and `--no-recursive`.
- `--workers` (default `max_concurrent_jobs`, 2).
- Per-file queue: extract audio (parallel) → Whisper (exclusive) → Gemma clean (exclusive).
- Combine **per parent folder** so `Course/P1L1/*.mp4` and `Course/P1L2/*.mp4` do not become one transcript.
- OCR ingest is a different command and still reads frames.
- Same-GPU warning: Whisper CUDA + Ollama on one GPU can OOM; `--workers 1` or `whisper_device: cpu`.

Keep `tests/test_cli_docs_consistency.py` happy: every documented `corpus …` example must still be a real command. Do not invent a `process_course` CLI.

**Definition of Done:**
- [ ] README / CLI.md / tools-usage / configuration describe queue, recursive discover, workers, per-parent combine, OCR vs transcribe.
- [ ] GPU OOM escape hatch is documented.
- [ ] `tests/test_cli_docs_consistency.py` passes.
- [ ] Tests written and passing for modified files
- [ ] No regressions in existing tests
