# Video Tool

Video transcription and visual OCR pipeline for extracting knowledge from lectures and presentations.

## CLI Commands

```bash
corpus tools video transcribe <directory>              # Transcribe (audio → Whisper)
corpus tools video pipeline <directory>                # Transcribe + clean (+ augment)
corpus tools video ingest <file> -c <collection>       # Ingest local video (visual OCR)
corpus tools video ingest-url <url> -c <collection>    # Download + ingest from URL (visual OCR)
corpus tools video jobs                                # List active jobs
corpus tools video status <job_id>                     # Check job status
```

`transcribe` and `pipeline` operate on a directory of media, discovering files
recursively by default (see below). `ingest` / `ingest-url` are the separate
**visual OCR** path that reads video **frames**, not audio.

## Features

- **Visual OCR**: Extracts text from slides, chalkboards, whiteboards using vision models
- **Scene detection**: Identifies frame transitions to avoid redundant processing
- **Math extraction**: Optional pix2tex fallback for LaTeX math expressions
- **YouTube support**: Download and process videos from URLs
- **Job management**: Background processing with status tracking
- **Auto-ingest**: Processed text automatically chunked and ingested into RAG collections

## Transcription vs. Visual OCR

The video tool has two distinct paths:

- **Transcription** (`corpus tools video transcribe`, and the lecture
  pipeline): converts spoken audio to text with Whisper. Before running
  Whisper, it demuxes an **audio-only** track with ffmpeg (`-vn`, video
  disabled) into `scratch_dir/audio/` and transcribes that WAV rather than the
  video container. This yields the 16 kHz mono PCM format speech models expect.
- **Visual OCR** (`corpus tools video ingest` / `ingest-url`): extracts video
  **frames** and reads slide/chalkboard/whiteboard text with a vision model.
  This path does not touch the audio-extraction settings.

### Audio extraction settings

Configured under `video:` in your config (see
[`docs/configuration.md`](../../../docs/configuration.md) and
[`configs/video.example.yaml`](../../../configs/video.example.yaml)):

| Key | Default | Description |
|-----|---------|-------------|
| `audio_sample_rate` | `16000` | Extracted WAV sample rate in Hz (Whisper expects 16000) |
| `audio_channels` | `1` | Extracted WAV channels (1 = mono, 2 = stereo) |
| `keep_extracted_audio` | `false` | Debug flag: keep WAVs under `scratch_dir/audio` instead of deleting them after transcription |
| `audio_timeout_seconds` | `1800` | ffmpeg kill deadline for audio extraction |

ffmpeg must be installed and on your `PATH`; extraction fails with a clear
error otherwise.

## Batch transcription: discovery, queue, and workers

`corpus tools video transcribe` and `corpus tools video pipeline` take a
directory (or single file) and process many videos at once.

**Recursive discovery (default).** The directory is scanned recursively for
supported extensions; directories named `scratch`, `.git`, and `__pycache__`
are skipped, as are symlinks. More than 500 matches is an error. Pass
`--no-recursive` to scan only the top-level folder.

**Per-parent combine.** Successful transcripts are combined **per parent
directory**, so a tree like:

```
Course/
├── P1L1/  a.mp4  b.mp4
└── P1L2/  c.mp4
```

produces one transcript for `Course/P1L1` and a separate one for
`Course/P1L2` — the two lectures are never merged. Combined files are written
under `paths.output_dir/<relative-parent>/` (`transcribe`) or
`paths.scratch_dir/video/<relative-parent>/` (`pipeline`), not next to the
MP4s. The cleaned pipeline file is named after the lecture folder
(`P1L1` → `p1l1_transcript.md`). A single input folder (or a single file)
keeps the legacy single-output path for the raw file.

**Concurrency (`--workers`).** Files run through a shared queue whose default
size is the `video.max_concurrent_jobs` config value (**2**). Override with
`--workers N`; `--workers 1` runs fully serially; the hard cap is **8**. Per
file the pipeline is:

1. **Extract audio** with ffmpeg — *parallel*, never gated.
2. **Whisper transcription** — *exclusive*, one file at a time.
3. **LLM clean** (Gemma; `pipeline` without `--skip-clean`) — *exclusive*,
   one at a time.

Whisper of one file may overlap LLM cleaning of another because they hold
different locks; a single shared Whisper weight load is reused across workers.
A failing file records its error and does not abort its siblings; the command
exits non-zero if any file failed.

```bash
corpus tools video transcribe ./Course --course BIOL101
corpus tools video transcribe ./Course --no-recursive
corpus tools video pipeline ./Course --workers 1
corpus tools video pipeline ./Course --skip-clean
```

> **Same-GPU note.** Running Whisper on CUDA while Ollama serves the cleaning
> model on the **same** GPU can exhaust VRAM (OOM). If you hit this, use
> `--workers 1` or move Whisper to CPU with `whisper_device: cpu` in config.

Visual OCR ingest (`corpus tools video ingest` / `ingest-url`) is a different
command that reads video frames and is unaffected by these discovery, queue,
and worker settings.

## Options

### Visual OCR (`ingest` / `ingest-url`)

| Option | Description | Default |
|--------|-------------|---------|
| `--collection, -c` | Target collection | (required) |
| `--threshold` | Scene detection sensitivity (0.0-1.0) | 0.3 |
| `--model` | Ollama vision model | llava |
| `--no-latex` | Disable pix2tex math fallback | false |
| `--context-window` | Adjacent frames per chunk | 1 |
| `--keep-frames` | Keep extracted frames after ingest | false |

### Transcription (`transcribe` / `pipeline`)

| Option | Description | Default |
|--------|-------------|---------|
| `--no-recursive` | Scan only the top-level folder | false (recurses) |
| `--workers` | Concurrent queue workers (capped at 8) | `video.max_concurrent_jobs` (2) |
| `--course, -c` | Course identifier (e.g. BIOL101) | none |
| `--lecture, -l` | Lecture number | none |
| `--clean` | (`transcribe`) run LLM cleaning after transcription | false |
| `--skip-clean` | (`pipeline`) skip the LLM cleaning step | false |
| `--augment` | (`pipeline`) open editor for manual augmentation | false |

## Architecture

```
video/
├── cli.py             # Click CLI commands
├── audio.py           # ffmpeg audio extract (transcription only)
├── discover.py        # Recursive media discovery
├── pipeline_queue.py  # Whisper / LLM mutex queue
├── transcribe.py      # Whisper transcription
├── clean.py           # LLM transcript cleaning
├── ingest.py          # Visual OCR ingestion
├── download.py        # URL download (yt-dlp)
├── extractor.py       # Frame extraction + scene detection
├── ocr.py             # Vision model OCR
├── postprocessor.py   # Text cleanup and deduplication
├── jobs.py            # OCR job queue
└── config.py          # Video-specific configuration
```

## Requirements

```bash
pip install corpusrag[video]  # Installs faster-whisper, Pillow, numpy
```

Also requires:
- ffmpeg on PATH (audio extract for `transcribe` / `pipeline`; frames for `ingest`)
- Ollama with a vision model (`ollama pull llava`) for visual OCR ingest only
