# Plan 23: Fast CLI Help, Audio-Only Transcription, Pipeline Queue

## Summary

`corpus --help` and nested `--help` still take several seconds because
`LazyGroup` loads every subcommand so Click can print short help, and
those modules import Chroma, Textual, RAG, and LLM stacks at import
time. Lazy loading the *command object* is not enough. This plan makes
help print from stored short-help strings, and moves heavy imports
behind command bodies so a help lookup does not look like the process
is hung.

Separately, lecture transcription feeds the whole MP4 to faster-whisper.
Audio transcription does not need the video stream. The transcribe path
will extract a 16 kHz mono WAV with ffmpeg (`-vn`) and run Whisper on
that file. Visual OCR ingest is unchanged and still extracts frames.

The folder pipeline today transcribes every file, then cleans the
combined transcript, so Whisper and Gemma never overlap. Discovery is
also non-recursive (`Path.iterdir()`), which misses nested lecture
trees. This plan scans the tree, queues each media file, and runs a
small worker pool with one mutex per model: Whisper exclusive, LLM
exclusive, so file 2 can transcribe while file 1 is being cleaned.

End state: `corpus --help` and `corpus tools --help` return in well
under a second without importing torch, chromadb, textual, or
faster-whisper. `corpus tools video pipeline ./Lectures` recursively
finds every MP4, extracts audio only, and pipelines Whisper + Gemma
across files.

## Goals

- `corpus --help`, `corpus tools --help`, and `corpus tools video --help`
  do not import `chromadb`, `textual`, `torch`, `faster_whisper`,
  `sentence_transformers`, or `transformers`.
- Help text for lazy subcommands still lists every command name and a
  one-line description (no empty Commands section).
- Transcription (CLI, lecture orchestrator, MCP `transcribe_video`)
  extracts audio with ffmpeg before Whisper; video frames are not
  decoded on this path.
- Directory inputs are discovered recursively (configurable) and
  submitted as one job per media file.
- A worker pool overlaps stages: audio extract is parallel; Whisper
  calls take a `whisper` lock; LLM clean calls take an `llm` lock.
- Existing single-file `corpus orchestrate lecture-pipeline <file>`
  behavior is preserved. Folder `process_course` uses the same queue
  for transcribe + clean.
- Tests cover help-import hygiene, ffmpeg audio extract (mocked),
  recursive discovery, mutex exclusion, and pipeline wiring.

## Non-Goals

- Do not move `torch` / `faster-whisper` / `sentence-transformers` out
  of main dependencies (plan 22 deferred that split; help will no
  longer import them).
- Do not change the visual OCR ingest path (`ingest`, `ingest-url`,
  keyframe extraction). That path still needs video frames.
- Do not add a GPU VRAM scheduler. Whisper CUDA + Ollama on the same
  GPU may OOM; document it, do not try to time-slice VRAM.
- Do not rewrite `tools.video.jobs.JobManager` (OCR background jobs).
  The transcription queue is a separate module.
- Do not add a new top-level CLI command or a `process_course` command.
  Directory support stays on `corpus tools video transcribe` /
  `pipeline` and on the existing `LecturePipelineOrchestrator.process_course`
  library method (plan 21).
- Do not parallelize across machines or add a persistent job broker.
- Do not change RAG retrieval, generators, TUI, or MCP tool lists
  except that `transcribe_video` picks up audio extract through
  `VideoTranscriber.transcribe_file`.

## Background / Context

Branch: `plan-23/dev` off `plan-22/sprint-1` (`fb9f784`).

Lazy loading already exists (`src/cli_lazy.py`, wired in `src/cli.py`,
`src/tools/cli.py`, `src/tools/learning/cli.py`). Click's
`Group.format_commands` still calls `get_command` for every listed
name so it can read `short_help`. That import currently pulls:

| Help command | What gets imported today |
|---|---|
| `corpus --help` | `db.management` (numpy + chromadb), `db.collections_cli` (rich + chromadb), `tools.cli`, `cli_dev`, `orchestrations.cli` (`cli_common` → chromadb) |
| `corpus tools --help` | all of the above plus `tools.rag.cli` (RAGAgent + Textual TUI), `tools.video.cli` (transcribe/clean/augment + chromadb), handwriting/summaries/learning CLIs |
| `corpus tools video --help` | `tools.video.cli` module-level `VideoTranscriber`, `TranscriptCleaner` (`llm.create_backend`), `cli_common` |

`cli_common.py` imports `ChromaDBBackend` at module level, and
`db/__init__.py` imports `chromadb` immediately. Any CLI module that
imports `load_cli_config` therefore pays Chroma on `--help`.

Transcription (`VideoTranscriber.transcribe_file`) passes the MP4 path
straight to `faster_whisper.WhisperModel.transcribe`. ffmpeg is already
required on PATH for OCR frame extract (`tools.video.extractor`). The
audio path should use the same binary with `-vn` (no video), 16 kHz
mono PCM — Whisper's native rate — written under `paths.scratch_dir`.

Folder processing is serial and shallow:

- `VideoTranscriber.transcribe_folder` and `process_course` use
  `Path.iterdir()`, not `rglob`. Nested trees such as
  `CS6300_Lectures/P1L1/*.mp4` are skipped if the parent is passed.
- `corpus tools video pipeline` transcribes every file, combines, then
  runs one `TranscriptCleaner.clean_file`. Whisper and Gemma never
  overlap.
- `max_concurrent_jobs` already exists on `VideoConfig` (default 2)
  but is only used by the OCR `JobManager`.

A course dump is typically many short MP4 segments per lecture folder.
Per-file Whisper + per-file clean, then combine **per parent
directory**, is how pipeline overlap actually happens without merging
P1L1 and P1L2 into one transcript.

### Recorded decisions

- **R1 — Help must not import:** `LazyGroup` stores
  `(import_path, short_help)` and overrides `format_commands` so listing
  help never calls `get_command`. Running a command still lazy-loads.
  String-only values remain valid (empty short help) for back-compat.
- **R2 — CLI modules are thin:** Click modules import `click` (and
  `cli_lazy` where needed) at module level. Config, db, transcriber,
  RAG, TUI, generators, and `cli_common` import inside the command
  function. `cli_common.load_cli_db` imports `ChromaDBBackend` inside
  the function; `db/__init__.py` lazy-loads chroma the same way
  `tools.rag` already lazy-loads `RAGAgent`.
- **R3 — Audio extract is transcription-only:** New
  `tools.video.audio.extract_audio`. `transcribe_file` always extracts
  first, then points Whisper at the WAV. OCR `extract_keyframes` is
  untouched. Default: 16 kHz, mono, PCM WAV, delete after success.
- **R4 — One job per media file, combine per parent dir:** Recursive
  discovery (`rglob`) is the default for directory inputs. Each file
  is a queue job (extract → transcribe → optional clean). After the
  queue drains, combine transcripts grouped by the file's parent
  directory so a course tree produces one combined file per lecture
  folder. A flat folder still produces one combined output.
- **R5 — Two mutexes, shared model instances:** One `VideoTranscriber`
  (one Whisper weights load) and one `TranscriptCleaner` are shared
  across workers. `whisper` lock around `transcribe_file`'s model
  call; `llm` lock around `clean` / `clean_file`. Audio extract does
  not take a model lock. Default `max_workers = VideoConfig.max_concurrent_jobs`
  (2).
- **R6 — ffmpeg stays list-argv:** No shell, no interpolated filter
  graphs. Paths are `Path` objects. Missing ffmpeg raises the same
  class of error as `extract_keyframes`. Missing audio stream fails
  that job without killing the queue.
- **R7 — lecture-pipeline CLI stays single-file:** Plan 21 left
  `process_course` as a library method. This plan reimplements
  `process_course` on the queue for transcribe+clean, then runs
  ingest/summary/flashcards/quiz per lecture sequentially under the
  `llm` lock. Do not add a folder CLI for orchestrate.

## Features / Tasks

### A1: LazyGroup help without importing subcommands
**Files:** `src/cli_lazy.py` (modify), `src/cli.py` (modify),
`src/tools/cli.py` (modify), `src/tools/learning/cli.py` (modify)
**Complexity:** S
**Depends on:** none

Change `lazy_subcommands` values to `str` (import path) or
`tuple[str, str]` (import path, short help). Override
`format_commands` to build the Commands table from stored short help
plus already-registered (non-lazy) commands via `super().get_command`.
Do not call `_load_lazy` from `format_commands` or `list_commands`.

Fill short-help strings from the current command docstrings:

- root: `tools`, `db`, `collections`, `dev`, `orchestrate`
- tools: `rag`, `video`, `handwriting`, `summaries`, `learning`
- learning: `flashcards`, `quizzes`

`get_command` / `_load_lazy` behavior and the ImportError stub group
stay. After A1, `corpus --help` still imports `db.management` until
A2/A3, but it must not import `tools.rag.cli` or `tools.video.cli`.

### A2: Defer heavy imports in Click modules
**Files:** `src/tools/rag/cli.py`, `src/tools/video/cli.py`,
`src/tools/summaries/cli.py`, `src/tools/flashcards/cli.py`,
`src/tools/quizzes/cli.py`, `src/tools/handwriting/cli.py`,
`src/db/management.py`, `src/db/collections_cli.py`,
`src/orchestrations/cli.py`
**Complexity:** M
**Depends on:** none

Module-level imports in these files must be limited to `click`,
`pathlib`/`typing` as needed, and `cli_lazy`. Move
`cli_common`, `RAGAgent`, `RAGApp`, `VideoTranscriber`,
`TranscriptCleaner`, `TranscriptAugmenter`, generators, `numpy`,
`ChromaDBBackend`, and `rich` into the command bodies (or a private
helper called from the body).

`tools.video.cli` today imports transcribe/clean/augment at the top;
that is why `corpus tools video --help` is slow. After this task those
imports happen only when `transcribe` / `clean` / `pipeline` / `augment`
run.

Keep command names, options, and help text identical so
`tests/test_cli_docs_consistency.py` and `tests/unit/test_cli.py` still
pass. Tests that patch `tools.video.cli.VideoTranscriber` (if any)
must patch the new in-function location or the implementation module.

### A3: Stop `cli_common` and `db` from importing Chroma at import time
**Files:** `src/cli_common.py` (modify), `src/db/__init__.py` (modify)
**Complexity:** S
**Depends on:** none

`cli_common.load_cli_config` must not import `ChromaDBBackend`.
`load_cli_db` imports it inside the function (or via `db.__getattr__`).
Mirror the existing `tools.rag.__getattr__` / `orchestrations.__getattr__`
pattern in `db/__init__.py` so `from db import DatabaseBackend` is
cheap and `from db import ChromaDBBackend` still works.

Do not change `chroma.py` itself. `tests/unit/test_tools.py` and
anything that does `from db import ChromaDBBackend` must keep working.

### A4: CLI startup hygiene tests
**Files:** `tests/unit/test_cli_startup.py` (new),
`tests/unit/test_cli.py` (modify if help assertions need the new
short-help wording)
**Complexity:** M
**Depends on:** A1, A2, A3

Run `--help` in a **subprocess** with `PYTHONPATH=src` so the parent
pytest process's imports cannot leak. Assert exit 0 and that
`sys.modules` after help does not contain:

`chromadb`, `textual`, `torch`, `faster_whisper`, `sentence_transformers`,
`transformers`

Cover at least:

- `corpus --help`
- `corpus tools --help`
- `corpus tools video --help`
- `corpus tools rag --help`

Also assert the help output still contains the lazy command names
(`tools`, `video`, `rag`, …). Do not assert a wall-clock budget in CI
(too noisy); the module blacklist is the contract. A comment in the
test may note the local target is sub-second.

### B1: ffmpeg audio extract helper
**Files:** `src/tools/video/audio.py` (new),
`tests/unit/test_audio.py` (new)
**Complexity:** M
**Depends on:** none

Add `extract_audio(video_path: Path, output_wav: Path, *, sample_rate: int = 16000, channels: int = 1) -> Path`.

ffmpeg argv (list form, no shell):

```
ffmpeg -y -nostdin -hide_banner -loglevel error
  -i <video> -vn -map 0:a:0 -ac <channels> -ar <sample_rate>
  -c:a pcm_s16le <output_wav>
```

- `FileNotFoundError` on the binary → `RuntimeError` matching
  `extract_keyframes` ("ffmpeg not found…").
- Non-zero ffmpeg exit (no audio stream, corrupt file) → raise with
  stderr snippet; caller decides whether to fail the job.
- Create parent dirs. Refuse to overwrite outside the intended
  output path via `Path` resolution (do not take a user string into
  the argv except the two paths).
- Tests mock `subprocess.run`: happy path, missing ffmpeg, non-zero
  exit, default rate/channels. Do not shell out to a real ffmpeg in
  unit tests.

Do not put this in `extractor.py` (that file is the OCR keyframe
path).

### B2: Transcribe from extracted audio
**Files:** `src/tools/video/transcribe.py` (modify),
`src/tools/video/config.py` (modify),
`tests/unit/test_video_config.py` (modify)
**Complexity:** M
**Depends on:** B1

`transcribe_file(video_path)`:

1. Resolve a WAV under `config.paths.scratch_dir / "audio" /
   <stem>_<sha-or-unique>.wav` (unique so two workers do not collide).
2. `extract_audio(...)`.
3. `WhisperModel.transcribe(str(wav_path), language=...)`.
4. Delete the WAV in a `finally` unless `config.keep_extracted_audio`
   is true.

Keep `_load_model` lazy. Keep `transcribe_folder` as a thin wrapper
that will be switched to the queue in C3; until then it can keep
calling `transcribe_file` per file (and therefore already gets audio
extract). MCP `transcribe_video` and `lecture_pipeline.process_lecture`
need no signature change.

Add to `VideoConfig` / `from_dict` / example YAML:

- `audio_sample_rate: 16000`
- `audio_channels: 1`
- `keep_extracted_audio: false`

Defaults match Whisper. OCR fields stay as they are.

### B3: Audio-extract config docs
**Files:** `configs/base.yaml` (modify),
`configs/base.example.yaml` (modify),
`configs/video.example.yaml` (modify),
`docs/configuration.md` (modify),
`src/tools/video/README.md` (modify)
**Complexity:** S
**Depends on:** B2

Document that transcription demuxes audio only, that ffmpeg must be
on PATH, and that `corpus tools video ingest` is the OCR path that
still reads frames. Mention `keep_extracted_audio` as a debug flag.

### C1: Recursive media discovery
**Files:** `src/tools/video/discover.py` (new),
`tests/unit/test_discover.py` (new)
**Complexity:** S
**Depends on:** none

`discover_media_files(root: Path, extensions: Sequence[str], *, recursive: bool = True) -> list[Path]`:

- File → `[root]` if suffix matches, else `FileNotFoundError`.
- Directory + `recursive=True` → `rglob("*")` filtered by suffix
  (case-insensitive).
- Directory + `recursive=False` → `iterdir()` (today's behavior).
- Skip directories named `scratch`, `.git`, `__pycache__`.
- Return a deterministically sorted list (`sorted` by path).
- Empty result → `FileNotFoundError` with the supported-extension
  list (same message shape as `transcribe_folder` today).

No ffmpeg, no Whisper. Pure pathlib so tests can use `tmp_path`.

### C2: Model mutexes and transcription queue
**Files:** `src/tools/video/pipeline_queue.py` (new),
`tests/unit/test_pipeline_queue.py` (new)
**Complexity:** L
**Depends on:** C1, B2

New types:

- `ModelGates`: `whisper` and `llm` `threading.Lock`s, exposed as
  context managers (`gates.whisper`, `gates.llm`).
- `TranscriptJob`: source path, optional course/lecture labels.
- `TranscriptJobResult`: source path, parent dir, raw text, cleaned
  text or None, error or None.
- `run_transcription_queue(files, *, transcriber, cleaner=None, skip_clean=False, max_workers=2, gates=None) -> list[TranscriptJobResult]`

Worker body, in order:

1. `transcriber.transcribe_file(path)` — the transcriber's Whisper
   call must run under `gates.whisper`. Implement the lock either
   inside `VideoTranscriber.transcribe_file` (injectable gates) or
   wrap the call in the worker. Prefer **injecting `ModelGates` into
   `VideoTranscriber` / `TranscriptCleaner`** so MCP and
   `process_lecture` get exclusion if a queue is running, and unit
   tests can pass a fake transcriber.
2. If not `skip_clean` and cleaner is set: `cleaner.clean(raw)` under
   `gates.llm`.
3. Record result. A failed file does not abort siblings; it is
   marked `error=` and the queue continues. After drain, if any job
   failed, raise a `TranscriptionQueueError` summarizing failures
   *after* successful files have been returned/written — or return
   results and let the CLI print failures and exit 1. Prefer return
   + CLI exit 1 so partial output is kept.

Use `ThreadPoolExecutor(max_workers)`. `max_workers=1` is valid
(serial, still uses audio extract). Share one transcriber and one
cleaner across workers (R5).

Tests (no real models):

- Two jobs: fake transcribe/clean with sleep + a thread-id/timestamp
  log; assert a clean of job A overlaps a transcribe of job B
  (whisper lock and llm lock are not the same lock).
- Two concurrent `transcribe` calls cannot be inside the whisper
  lock at the same time (barrier/event test).
- One failure among three files: two results succeed, one has error.
- `skip_clean=True` never calls cleaner.

Do not use `JobManager`. Do not persist jobs to disk.

### C3: Wire video CLI transcribe + pipeline to the queue
**Files:** `src/tools/video/cli.py` (modify),
`src/tools/video/transcribe.py` (modify `transcribe_folder` /
`combine_transcripts`),
`src/tools/video/config.py` (modify if `recursive` needs a field),
`tests/unit/test_video_cli.py` (modify)
**Complexity:** M
**Depends on:** C2, A2

`transcribe` and `pipeline`:

1. `discover_media_files(input, cfg.supported_extensions, recursive=True)`
   (`--no-recursive` flag to restore `iterdir`).
2. Echo the count ("Queued N videos…") before any model load.
3. `run_transcription_queue(...)` with `skip_clean` inverted from
   `pipeline --skip-clean` / `transcribe --clean`.
4. Group successful results by `parent` directory. For each group,
   `combine_transcripts` and write:
   - pipeline: `scratch/<folder>/transcript_raw.md` and, if cleaned,
     `transcript_cleaned.md` as today, but one pair **per parent
     folder** when the input was a tree.
   - transcribe: existing output path logic when the input is a
     single folder; for a tree, write
     `output_dir / <parent.name> / transcript.md` (document this).
5. Print per-file success/fail. Exit 1 if any file failed.

`--workers` option (default `cfg.max_concurrent_jobs`) on both
commands. Augment step of `pipeline` stays serial and only runs when
`--augment` is set, on each cleaned/combined file.

Update `combine_transcripts` only as needed to accept a dict that is
a subset of files (one parent group). Keep markdown shape
(`## Segment i: filename`).

### C4: Lecture `process_course` uses the same queue
**Files:** `src/orchestrations/lecture_pipeline.py` (modify),
`tests/test_lecture_pipeline_config.py` (modify),
`tests/unit/test_orchestrations.py` (modify)
**Complexity:** M
**Depends on:** C2

`process_course(video_folder, ...)`:

1. Discover files with `discover_media_files` (recursive default).
2. Run transcribe+clean through `run_transcription_queue` (one shared
   transcriber/cleaner, same gates).
3. For each successful file, in sorted order, run ingest / summary /
   flashcards / quiz as `process_lecture` does today. Those LLM calls
   take the `llm` lock so they cannot overlap a clean still in flight
   if any (simplest: wait for the transcribe queue to finish, then
   generate sequentially — no overlap between generators and
   Whisper). That is enough: Whisper/Gemma overlap happens in step 2.

Keep `process_lecture` (single file) working. It should extract audio
via `transcribe_file` (B2) and does not need the executor.

Do not add orchestrate CLI flags (R7). Tests mock transcriber/cleaner
as they do now; assert `process_course` on a nested tmp tree sees
files in subfolders and calls transcribe once per file.

### C5: Queue / discovery docs
**Files:** `src/tools/video/README.md` (modify),
`src/CLI.md` (modify),
`docs/tools-usage.md` (modify),
`docs/configuration.md` (modify)
**Complexity:** S
**Depends on:** C3, C4

Document recursive discovery, `--no-recursive`, `--workers`, per-file
queue with Whisper/LLM mutexes, per-parent combine, and that OCR
ingest is a different command. Note: running Whisper on CUDA and
Ollama on the same GPU at once can OOM; set `--workers 1` or put
Whisper on CPU if that happens.

## New Dependencies

| Package | Feature | Optional? |
|---|---|---|
| *(none)* | ffmpeg is already a runtime requirement for video | already required on PATH |

No new PyPI packages. `threading` / `concurrent.futures` are stdlib.

## File Change Summary

| File | Action |
|---|---|
| `src/cli_lazy.py` | modify |
| `src/cli.py` | modify |
| `src/cli_common.py` | modify |
| `src/tools/cli.py` | modify |
| `src/tools/learning/cli.py` | modify |
| `src/tools/rag/cli.py` | modify |
| `src/tools/video/cli.py` | modify |
| `src/tools/video/audio.py` | new |
| `src/tools/video/discover.py` | new |
| `src/tools/video/pipeline_queue.py` | new |
| `src/tools/video/transcribe.py` | modify |
| `src/tools/video/config.py` | modify |
| `src/tools/video/README.md` | modify |
| `src/tools/summaries/cli.py` | modify |
| `src/tools/flashcards/cli.py` | modify |
| `src/tools/quizzes/cli.py` | modify |
| `src/tools/handwriting/cli.py` | modify |
| `src/db/__init__.py` | modify |
| `src/db/management.py` | modify |
| `src/db/collections_cli.py` | modify |
| `src/orchestrations/cli.py` | modify |
| `src/orchestrations/lecture_pipeline.py` | modify |
| `src/CLI.md` | modify |
| `configs/base.yaml` | modify |
| `configs/base.example.yaml` | modify |
| `configs/video.example.yaml` | modify |
| `docs/configuration.md` | modify |
| `docs/tools-usage.md` | modify |
| `tests/unit/test_cli_startup.py` | new |
| `tests/unit/test_audio.py` | new |
| `tests/unit/test_discover.py` | new |
| `tests/unit/test_pipeline_queue.py` | new |
| `tests/unit/test_cli.py` | modify |
| `tests/unit/test_video_cli.py` | modify |
| `tests/unit/test_video_config.py` | modify |
| `tests/unit/test_orchestrations.py` | modify |
| `tests/test_lecture_pipeline_config.py` | modify |

## Open Questions

- **Same-GPU OOM:** Default is to *allow* Whisper and Gemma to overlap
  (that is the point of two mutexes). If local runs OOM, the escape
  hatch is `--workers 1` or `whisper_device: cpu`. Revisit a third
  `gpu` lock only if that shows up in real lecture runs.
- **Combine granularity:** R4 combines per parent directory. If a
  lecture is split across nested subfolders, those would not merge.
  Confirm that "one folder = one lecture's segments" matches how
  dumps are laid out (`P1L1/*.mp4`).
- **`process_course` after the queue:** Step 3 waits for all
  transcribe+clean jobs, then generates study materials serially.
  Overlapping flashcard generation with later Whisper jobs is
  possible but contends on the `llm` lock and on Chroma writes; left
  out on purpose.
- **Help strings vs. docstring drift:** Short help is duplicated into
  the lazy map. A4 checks names are present; it does not check that
  the sentence matches the loaded command's docstring. Acceptable.
- **faster-whisper still in main deps:** `tests/test_optional_extras.py`
  already asserts it is *not* in main dependencies, but `pyproject.toml`
  currently lists it there. Out of scope here; do not "fix" extras in
  this plan unless a sprint is already touching `pyproject.toml`.
