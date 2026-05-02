# Video Ingestion Pipeline — Technical Specification

**Project:** CorpusRAG  
**Feature:** `corpus video ingest`  
**Status:** Ready for implementation  
**Depends on:** R1 (rename), T1 (hierarchical tag parser)

---

## Overview

The video ingestion pipeline converts lecture recordings, open courseware videos, and screen-capture content into structured, searchable markdown stored in ChromaDB. The pipeline is fully local — no API calls required — and is designed to handle the three primary content modalities found in educational video:

1. **Slide-based lectures** — static or animated slides, usually high-contrast text
2. **Chalkboard / whiteboard lectures** — handwritten content, often math-heavy
3. **Mixed format** — talking head with projected slides or screen sharing

The pipeline does not attempt to transcribe speech. It focuses exclusively on visual instructional content — what is written, drawn, or displayed on screen. Speech transcription (via Whisper) is a separate optional track that can be composed with this pipeline.

---

## Architecture

```
MP4 File
    │
    ▼
┌─────────────────────┐
│  Scene Change        │  FFmpeg select filter
│  Detection           │  Extracts frames only on visual change
└─────────┬───────────┘
          │  JPEG frames
          ▼
┌─────────────────────┐
│  Frame Classifier    │  Lightweight heuristic or small vision model
│                      │  Determines: slide / chalkboard / no_content
└─────────┬───────────┘
          │  Classified frames
          ▼
┌─────────────────────┐
│  Vision OCR          │  Ollama + llava (primary)
│                      │  Routes math frames to pix2tex (fallback)
└─────────┬───────────┘
          │  Raw markdown per frame
          ▼
┌─────────────────────┐
│  Post-processor      │  Deduplication, formatting, timestamp attachment
└─────────┬───────────┘
          │  Clean markdown chunks
          ▼
┌─────────────────────┐
│  Parent-Child        │  Full lecture = parent doc
│  Chunker             │  Per-frame segments = child chunks
└─────────┬───────────┘
          │  Structured chunks + metadata
          ▼
┌─────────────────────┐
│  ChromaDB Ingest     │  Reuses existing agent.ingest_text()
│                      │  SHA-256 hash for incremental sync
└─────────────────────┘
```

---

## Directory Structure

```
src/corpus_rag/tools/video/
├── __init__.py
├── ingest_video.py        # Pipeline orchestrator — main entry point
├── extractor.py           # FFmpeg frame extraction
├── classifier.py          # Frame type classification
├── ocr.py                 # Vision OCR (llava + pix2tex)
├── postprocessor.py       # Deduplication, formatting, timestamp math
├── chunker.py             # Parent-child chunking for video content
└── cli.py                 # Click commands: corpus video ingest / info
```

---

## Step 1 — Scene Change Detection

### Why Scene Detection Instead of Fixed FPS

Extracting at a fixed frame rate (e.g., 1 frame/second) for a 90-minute lecture produces ~5,400 frames, most of which are identical. Scene change detection extracts a frame only when the visual content changes significantly, typically yielding 50–200 frames for a standard lecture — one per slide transition or meaningful chalkboard update.

### Implementation

```python
# extractor.py

import subprocess
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ExtractedFrame:
    path: Path
    frame_index: int          # Sequential index among extracted frames
    source_timestamp_sec: float  # Wall-clock position in source video


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    scene_threshold: float = 0.3,
    min_interval_sec: float = 2.0,
) -> list[ExtractedFrame]:
    """
    Extract frames at scene change boundaries using FFmpeg.

    Args:
        video_path: Path to source MP4 file.
        output_dir: Directory to write JPEG frames.
        scene_threshold: Sensitivity (0.0–1.0). Lower = more frames.
                         0.3 is a good default for lecture content.
                         Use 0.15 for fast chalkboard writing.
                         Use 0.4 for slow slide-based lectures.
        min_interval_sec: Minimum seconds between extracted frames.
                          Prevents burst extraction on rapid transitions.

    Returns:
        List of ExtractedFrame with path and timestamp metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%06d.jpg")

    # Extract frames + write timestamp sidecar file
    timestamp_file = output_dir / "timestamps.txt"

    subprocess.run([
        "ffmpeg", "-i", str(video_path),
        "-vf", (
            f"select=gt(scene\\,{scene_threshold}),"
            f"select=isnan(prev_selected_t)+gte(t-prev_selected_t\\,{min_interval_sec})"
        ),
        "-vsync", "vfr",
        "-frame_pts", "1",
        output_pattern,
    ], check=True, capture_output=True)

    # FFmpeg doesn't write timestamps directly — derive from pts metadata
    # Use showinfo filter to extract presentation timestamps
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-select_streams", "v",
        "-show_entries", "frame=pts_time,pkt_pts_time",
        "-of", "csv=p=0",
        str(video_path),
    ], capture_output=True, text=True)

    frame_paths = sorted(output_dir.glob("frame_*.jpg"))
    timestamps = _parse_ffprobe_timestamps(result.stdout, len(frame_paths))

    return [
        ExtractedFrame(path=p, frame_index=i, source_timestamp_sec=t)
        for i, (p, t) in enumerate(zip(frame_paths, timestamps))
    ]


def _parse_ffprobe_timestamps(ffprobe_output: str, n_frames: int) -> list[float]:
    """Parse pts_time values from ffprobe csv output."""
    times = []
    for line in ffprobe_output.strip().splitlines():
        parts = line.split(",")
        for part in parts:
            try:
                times.append(float(part))
                break
            except ValueError:
                continue
    # If parsing fails, generate evenly spaced fallback timestamps
    if len(times) < n_frames:
        times = [i * 5.0 for i in range(n_frames)]
    return times[:n_frames]


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS string for metadata and display."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
```

### Threshold Tuning Guide

| Content Type | Recommended Threshold | Expected Frame Count (90min) |
|---|---|---|
| Slide-based, slow pace | 0.4 | 40–80 |
| Slide-based, fast pace | 0.25 | 80–150 |
| Chalkboard, writing continuously | 0.15 | 150–300 |
| Mixed slide + chalkboard | 0.25 | 100–200 |
| Screen recording / code | 0.3 | 50–120 |

Users can override threshold via CLI flag `--threshold`. The pipeline logs the frame count after extraction so users can re-run with a different threshold if too few or too many frames are captured.

---

## Step 2 — Frame Classification

Before sending every frame to a vision model (which is expensive), classify each frame into one of four categories using lightweight heuristics. Only frames with instructional content are sent to OCR.

### Categories

| Class | Description | OCR Path |
|---|---|---|
| `slide` | Digital slide with clean text and high contrast | llava primary |
| `chalkboard` | Handwritten content on dark background | llava + pix2tex fallback |
| `whiteboard` | Handwritten content on light background | llava + pix2tex fallback |
| `no_content` | Speaker face, audience, black screen, title card only | Skip |

### Heuristic Classifier

```python
# classifier.py

from enum import Enum
from pathlib import Path
import numpy as np
from PIL import Image


class FrameType(Enum):
    SLIDE = "slide"
    CHALKBOARD = "chalkboard"
    WHITEBOARD = "whiteboard"
    NO_CONTENT = "no_content"


def classify_frame(frame_path: Path) -> FrameType:
    """
    Classify a frame using pixel-level heuristics.
    Fast enough to run on every extracted frame without GPU.
    """
    img = Image.open(frame_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    mean_brightness = arr.mean()
    # Dark background = chalkboard candidate
    if mean_brightness < 60:
        return FrameType.CHALKBOARD

    # Very bright, high contrast = slide candidate
    if mean_brightness > 180:
        std = arr.std()
        if std > 40:
            return FrameType.SLIDE
        # Very uniform brightness = blank or title-only frame
        return FrameType.NO_CONTENT

    # Mid-range brightness = whiteboard or mixed
    # Use edge density as proxy for content presence
    edges = _edge_density(arr)
    if edges > 0.05:
        return FrameType.WHITEBOARD
    return FrameType.NO_CONTENT


def _edge_density(arr: np.ndarray) -> float:
    """Simple Sobel-based edge density. Values >0.05 indicate text/drawing."""
    gray = arr.mean(axis=2)
    # Horizontal and vertical gradients
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    return float((gx + gy) / 2 / 255)
```

**Note:** The heuristic classifier is intentionally simple. For high-accuracy use cases, replace `classify_frame()` with a call to a small CLIP model or a dedicated scene classifier. The interface (`frame_path → FrameType`) is the same regardless of backend.

---

## Step 3 — Vision OCR

### Primary: llava via Ollama

```python
# ocr.py

import base64
import ollama
from pathlib import Path
from corpus_rag.tools.video.classifier import FrameType


SLIDE_PROMPT = """
This is a frame from a lecture video showing a presentation slide.
Transcribe ALL text visible on the slide exactly as written.
Preserve the visual hierarchy: use # for slide titles, ## for section headers,
and regular text or bullet points for body content.
Use LaTeX notation for any mathematical expressions: inline as $expr$ and
display equations as $$expr$$.
Do not describe images or diagrams — only transcribe text.
If the slide contains no readable text, respond with exactly: [NO_CONTENT]
"""

CHALKBOARD_PROMPT = """
This is a frame from a lecture video showing a chalkboard or whiteboard.
Transcribe all visible text, equations, and diagrams.
For mathematical notation, use LaTeX: inline as $expr$, display as $$expr$$.
For diagrams, describe them concisely in square brackets: [Diagram: description].
Preserve the spatial layout where it conveys meaning (e.g., matrix notation).
If nothing instructional is visible, respond with exactly: [NO_CONTENT]
"""

MATH_DETECTION_THRESHOLD = 0.25  # If >25% of OCR output is LaTeX, flag as math-heavy


def ocr_frame(
    frame_path: Path,
    frame_type: FrameType,
    model: str = "llava",
) -> tuple[str, bool]:
    """
    Run vision OCR on a single frame.

    Returns:
        (transcribed_text, is_math_heavy)
        is_math_heavy signals whether pix2tex fallback should run.
    """
    prompt = SLIDE_PROMPT if frame_type == FrameType.SLIDE else CHALKBOARD_PROMPT

    with open(frame_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    response = ollama.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [image_b64],
        }]
    )

    text = response["message"]["content"].strip()

    # Detect math-heavy output for pix2tex fallback routing
    latex_chars = text.count("$") + text.count("\\")
    is_math_heavy = (latex_chars / max(len(text), 1)) > MATH_DETECTION_THRESHOLD

    return text, is_math_heavy
```

### Math Fallback: pix2tex

pix2tex is a dedicated equation OCR model trained specifically on mathematical notation. It significantly outperforms general vision models on dense math content.

```python
# ocr.py (continued)

from PIL import Image

_latex_model = None  # Lazy-loaded — avoids slow import on non-math content


def ocr_frame_latex(frame_path: Path) -> str:
    """
    Specialized LaTeX extraction using pix2tex.
    Use when llava output is math-heavy or when frame_type is CHALKBOARD.
    """
    global _latex_model
    if _latex_model is None:
        from pix2tex.cli import LatexOCR
        _latex_model = LatexOCR()

    img = Image.open(frame_path)
    try:
        latex = _latex_model(img)
        return f"$$\n{latex}\n$$"
    except Exception:
        return ""  # Fall through to llava result if pix2tex fails


def ocr_frame_with_fallback(
    frame_path: Path,
    frame_type: FrameType,
    model: str = "llava",
    use_latex_fallback: bool = True,
) -> str:
    """
    Full OCR with optional pix2tex fallback for math content.
    This is the primary function called by the pipeline orchestrator.
    """
    text, is_math_heavy = ocr_frame(frame_path, frame_type, model)

    if text == "[NO_CONTENT]":
        return "[NO_CONTENT]"

    if use_latex_fallback and is_math_heavy and frame_type in (
        FrameType.CHALKBOARD, FrameType.WHITEBOARD
    ):
        latex_text = ocr_frame_latex(frame_path)
        if latex_text:
            # Merge: use llava for surrounding text, pix2tex for the equation block
            return f"{text}\n\n{latex_text}"

    return text
```

### OCR Quality Considerations

**Resolution matters:** llava performs significantly better on high-resolution frames. If the source video is 720p or lower, upscale frames before OCR:

```python
from PIL import Image

def upscale_frame(frame_path: Path, target_width: int = 1920) -> Path:
    """Upscale frame to improve OCR accuracy on low-res sources."""
    img = Image.open(frame_path)
    if img.width < target_width:
        ratio = target_width / img.width
        new_size = (target_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        upscaled_path = frame_path.with_stem(frame_path.stem + "_upscaled")
        img.save(upscaled_path, quality=95)
        return upscaled_path
    return frame_path
```

**Model alternatives:**

| Model | Speed | Math Quality | Text Quality | Notes |
|---|---|---|---|---|
| `llava` (7B) | Medium | Fair | Good | Default, best balance |
| `llava` (13B) | Slow | Better | Better | Use if 7B misses content |
| `bakllava` | Fast | Poor | Good | For fast slides only |
| `moondream` | Very fast | Poor | Fair | Minimal VRAM |
| Claude vision API | Fast | Excellent | Excellent | Non-local, costs money |

---

## Step 4 — Post-Processing

Raw OCR output per frame needs cleaning before ingest: deduplication of near-identical frames, formatting normalization, and timestamp attachment.

```python
# postprocessor.py

from dataclasses import dataclass
from pathlib import Path
from corpus_rag.tools.video.extractor import ExtractedFrame, format_timestamp
import hashlib


@dataclass
class ProcessedChunk:
    content: str
    frame_index: int
    timestamp_sec: float
    timestamp_str: str       # HH:MM:SS
    source_file: str
    frame_type: str
    content_hash: str        # SHA-256 of content, for deduplication


def deduplicate_chunks(chunks: list[ProcessedChunk], similarity_threshold: float = 0.85) -> list[ProcessedChunk]:
    """
    Remove near-duplicate chunks (same slide captured twice).
    Uses character-level Jaccard similarity as a fast heuristic.
    """
    seen: list[ProcessedChunk] = []
    for chunk in chunks:
        if not seen:
            seen.append(chunk)
            continue
        prev = seen[-1]
        similarity = _jaccard(chunk.content, prev.content)
        if similarity < similarity_threshold:
            seen.append(chunk)
    return seen


def _jaccard(a: str, b: str) -> float:
    """Character n-gram Jaccard similarity."""
    ngrams_a = set(_ngrams(a, 3))
    ngrams_b = set(_ngrams(b, 3))
    if not ngrams_a and not ngrams_b:
        return 1.0
    if not ngrams_a or not ngrams_b:
        return 0.0
    return len(ngrams_a & ngrams_b) / len(ngrams_a | ngrams_b)


def _ngrams(text: str, n: int) -> list[str]:
    text = text.lower().replace(" ", "")
    return [text[i:i+n] for i in range(len(text) - n + 1)]


def build_chunk(
    text: str,
    frame: ExtractedFrame,
    frame_type: str,
    source_file: Path,
) -> ProcessedChunk:
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return ProcessedChunk(
        content=text,
        frame_index=frame.frame_index,
        timestamp_sec=frame.source_timestamp_sec,
        timestamp_str=format_timestamp(frame.source_timestamp_sec),
        source_file=str(source_file),
        frame_type=frame_type,
        content_hash=content_hash,
    )


def format_chunk_markdown(chunk: ProcessedChunk) -> str:
    """Wrap chunk content with timestamp annotation for storage."""
    return (
        f"<!-- timestamp: {chunk.timestamp_str} | frame: {chunk.frame_index} -->\n"
        f"{chunk.content}"
    )
```

---

## Step 5 — Parent-Child Chunking

The parent-child retrieval pattern already used in CorpusRAG applies naturally to video:

- **Parent document:** the full lecture markdown (all frames concatenated), stored in `LocalFileStore`
- **Child chunks:** individual frame segments, indexed in ChromaDB for vector search

This means a query like *"explain the softmax function"* retrieves the specific slide frame where softmax is discussed, but the LLM receives surrounding context (adjacent frames) to understand the explanation flow.

```python
# chunker.py

from dataclasses import dataclass
from corpus_rag.tools.video.postprocessor import ProcessedChunk, format_chunk_markdown


@dataclass
class VideoParentDoc:
    content: str           # Full lecture markdown
    source_file: str
    total_frames: int
    duration_sec: float
    metadata: dict


@dataclass
class VideoChildChunk:
    content: str           # Single frame markdown
    parent_id: str         # Reference to parent doc
    metadata: dict         # ChromaDB metadata


def build_parent_doc(
    chunks: list[ProcessedChunk],
    source_file: str,
    duration_sec: float,
) -> VideoParentDoc:
    """
    Assemble full lecture markdown from processed chunks.
    This is stored in LocalFileStore as the parent document.
    """
    sections = [format_chunk_markdown(c) for c in chunks]
    full_content = "\n\n---\n\n".join(sections)

    return VideoParentDoc(
        content=full_content,
        source_file=source_file,
        total_frames=len(chunks),
        duration_sec=duration_sec,
        metadata={
            "source_file": source_file,
            "source_type": "video",
            "total_frames": len(chunks),
            "duration_sec": duration_sec,
        }
    )


def build_child_chunks(
    chunks: list[ProcessedChunk],
    parent_id: str,
    source_file: str,
    context_window: int = 1,
) -> list[VideoChildChunk]:
    """
    Build child chunks with optional adjacent frame context.

    context_window: Number of adjacent frames to include as context.
                    0 = frame only, 1 = frame + 1 before + 1 after.
    """
    result = []
    for i, chunk in enumerate(chunks):
        # Include adjacent frames as context
        start = max(0, i - context_window)
        end = min(len(chunks), i + context_window + 1)
        context_chunks = chunks[start:end]
        content_with_context = "\n\n".join(
            format_chunk_markdown(c) for c in context_chunks
        )

        result.append(VideoChildChunk(
            content=content_with_context,
            parent_id=parent_id,
            metadata={
                "source_file": source_file,
                "source_type": "video",
                "frame_index": chunk.frame_index,
                "timestamp_sec": chunk.timestamp_sec,
                "timestamp_str": chunk.timestamp_str,
                "frame_type": chunk.frame_type,
                "content_hash": chunk.content_hash,
                "parent_id": parent_id,
            }
        ))
    return result
```

---

## Step 6 — Pipeline Orchestrator

```python
# ingest_video.py

import shutil
import logging
from dataclasses import dataclass
from pathlib import Path

from corpus_rag.tools.video.extractor import extract_keyframes
from corpus_rag.tools.video.classifier import classify_frame, FrameType
from corpus_rag.tools.video.ocr import ocr_frame_with_fallback
from corpus_rag.tools.video.postprocessor import build_chunk, deduplicate_chunks
from corpus_rag.tools.video.chunker import build_parent_doc, build_child_chunks

logger = logging.getLogger(__name__)


@dataclass
class VideoIngestResult:
    source_file: str
    frames_extracted: int
    frames_skipped: int
    chunks_after_dedup: int
    collection: str
    duration_sec: float


def ingest_video(
    video_path: Path,
    collection: str,
    agent,
    scene_threshold: float = 0.3,
    vision_model: str = "llava",
    use_latex_fallback: bool = True,
    context_window: int = 1,
    cleanup_frames: bool = True,
) -> VideoIngestResult:
    """
    Full pipeline: MP4 → ChromaDB.

    Args:
        video_path: Path to source video file.
        collection: Target ChromaDB collection name.
        agent: Initialized CorpusRAG Agent instance.
        scene_threshold: FFmpeg scene change sensitivity (0.0–1.0).
        vision_model: Ollama model for OCR (default: llava).
        use_latex_fallback: Whether to run pix2tex on math-heavy frames.
        context_window: Adjacent frames to include per child chunk.
        cleanup_frames: Delete temp frames dir after ingest.
    """
    frames_dir = Path("/tmp/corpus_rag_frames") / video_path.stem
    logger.info(f"Starting video ingest: {video_path.name}")

    # Step 1: Extract keyframes
    logger.info("Extracting keyframes...")
    frames = extract_keyframes(video_path, frames_dir, scene_threshold)
    logger.info(f"Extracted {len(frames)} frames")

    # Step 2 + 3: Classify and OCR each frame
    raw_chunks = []
    skipped = 0

    for frame in frames:
        frame_type = classify_frame(frame.path)

        if frame_type == FrameType.NO_CONTENT:
            skipped += 1
            logger.debug(f"Skipping frame {frame.frame_index} (no content)")
            continue

        logger.debug(f"OCR frame {frame.frame_index} ({frame_type.value})")
        text = ocr_frame_with_fallback(
            frame.path,
            frame_type,
            model=vision_model,
            use_latex_fallback=use_latex_fallback,
        )

        if text == "[NO_CONTENT]":
            skipped += 1
            continue

        raw_chunks.append(build_chunk(
            text=text,
            frame=frame,
            frame_type=frame_type.value,
            source_file=video_path,
        ))

    logger.info(f"OCR complete. {len(raw_chunks)} chunks, {skipped} skipped")

    # Step 4: Deduplicate
    chunks = deduplicate_chunks(raw_chunks)
    logger.info(f"After dedup: {len(chunks)} chunks")

    # Step 5: Build parent doc
    duration_sec = frames[-1].source_timestamp_sec if frames else 0.0
    parent_doc = build_parent_doc(chunks, str(video_path), duration_sec)
    parent_id = f"video:{video_path.stem}"

    # Step 6: Build child chunks
    child_chunks = build_child_chunks(chunks, parent_id, str(video_path), context_window)

    # Step 7: Ingest into ChromaDB via existing agent
    agent.ingest_text(
        text=parent_doc.content,
        collection=collection,
        doc_id=parent_id,
        metadata=parent_doc.metadata,
    )

    for child in child_chunks:
        agent.ingest_text(
            text=child.content,
            collection=collection,
            metadata=child.metadata,
        )

    # Cleanup
    if cleanup_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
        logger.info("Temp frames cleaned up")

    return VideoIngestResult(
        source_file=str(video_path),
        frames_extracted=len(frames),
        frames_skipped=skipped,
        chunks_after_dedup=len(chunks),
        collection=collection,
        duration_sec=duration_sec,
    )
```

---

## Step 7 — CLI Integration

```python
# tools/video/cli.py

import click
from pathlib import Path
from corpus_rag.tools.video.ingest_video import ingest_video
from corpus_rag.agent import Agent
from corpus_rag.config import load_config


@click.group()
def video():
    """Video ingestion tools."""
    pass


@video.command("ingest")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("--collection", "-c", default="notes", show_default=True,
              help="Target ChromaDB collection name.")
@click.option("--threshold", default=0.3, show_default=True,
              help="Scene change sensitivity (0.0–1.0). Lower = more frames.")
@click.option("--model", default="llava", show_default=True,
              help="Ollama vision model to use for OCR.")
@click.option("--no-latex", is_flag=True, default=False,
              help="Disable pix2tex LaTeX fallback for math content.")
@click.option("--context-window", default=1, show_default=True,
              help="Adjacent frames to include per child chunk (0 = frame only).")
@click.option("--keep-frames", is_flag=True, default=False,
              help="Keep extracted frames after ingest (for debugging).")
def ingest_cmd(video_path, collection, threshold, model, no_latex, context_window, keep_frames):
    """
    Ingest a video file into a CorpusRAG collection.

    Extracts keyframes on scene changes, runs vision OCR,
    and stores structured markdown in ChromaDB.

    Examples:

      corpus video ingest lecture.mp4 --collection cs6301

      corpus video ingest lecture.mp4 --threshold 0.15 --collection math101

      corpus video ingest lecture.mp4 --model llava:13b --no-latex
    """
    config = load_config()
    agent = Agent(config)

    click.echo(f"Ingesting {video_path.name} → collection '{collection}'")
    click.echo(f"Scene threshold: {threshold} | Model: {model}")

    with click.progressbar(length=100, label="Processing") as bar:
        result = ingest_video(
            video_path=video_path,
            collection=collection,
            agent=agent,
            scene_threshold=threshold,
            vision_model=model,
            use_latex_fallback=not no_latex,
            context_window=context_window,
            cleanup_frames=not keep_frames,
        )
        bar.update(100)

    click.echo(f"\n✓ Ingest complete")
    click.echo(f"  Frames extracted:    {result.frames_extracted}")
    click.echo(f"  Frames skipped:      {result.frames_skipped}")
    click.echo(f"  Chunks stored:       {result.chunks_after_dedup}")
    click.echo(f"  Video duration:      {result.duration_sec:.0f}s")
    click.echo(f"  Collection:          {result.collection}")
```

Wire into main CLI in `src/corpus_rag/cli.py`:

```python
from corpus_rag.tools.video.cli import video
cli.add_command(video)
```

And as a TUI slash command:

```python
# slash_commands.py

@slash_command("ingest", "Ingest a file or video into the active collection")
def handle_ingest(args: list[str]) -> SlashCommandResult:
    if not args:
        return SlashCommandResult(type="error", content="Usage: /ingest <path> [--collection <name>]")
    path = Path(args[0])
    if path.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi"):
        # Route to video pipeline
        ...
    else:
        # Route to existing file ingest
        ...
```

---

## ChromaDB Metadata Schema for Video Chunks

Every child chunk stored in ChromaDB carries the following metadata fields:

| Field | Type | Example | Purpose |
|---|---|---|---|
| `source_file` | `str` | `"/vault/lecture_week3.mp4"` | Source attribution |
| `source_type` | `str` | `"video"` | Filter video vs text chunks |
| `frame_index` | `int` | `42` | Frame sequence position |
| `timestamp_sec` | `float` | `1523.4` | Position in video (seconds) |
| `timestamp_str` | `str` | `"00:25:23"` | Human-readable timestamp |
| `frame_type` | `str` | `"chalkboard"` | `slide` / `chalkboard` / `whiteboard` |
| `content_hash` | `str` | `"a3f4b2c1..."` | Deduplication fingerprint |
| `parent_id` | `str` | `"video:lecture_week3"` | Link to parent doc in LocalFileStore |

### Example Queries Using Video Metadata

```python
# Find all video chunks from a specific lecture
{"source_file": {"$contains": "lecture_week3.mp4"}}

# Find only slide frames (not chalkboard)
{"$and": [
    {"source_type": {"$eq": "video"}},
    {"frame_type": {"$eq": "slide"}},
]}

# Find chunks in the first 30 minutes
{"$and": [
    {"source_type": {"$eq": "video"}},
    {"timestamp_sec": {"$lt": 1800}},
]}

# Mix video and text chunks in one query (no filter = searches all)
# Just query normally — video chunks are stored alongside text chunks
```

---

## Dependencies and Installation

```toml
# pyproject.toml

[project.optional-dependencies]
video = [
    "ffmpeg-python>=0.2.0",
    "ollama>=0.1.0",
    "Pillow>=10.0.0",
    "numpy>=1.24.0",
    "pix2tex>=0.1.2",
]
```

```bash
# Install with video support
pip install corpusrag[video]

# System dependency — must be installed separately
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
apt install ffmpeg

# Pull the vision model
ollama pull llava
```

---

## Open Questions and Future Work

### Resolved in This Spec

- ✅ Timestamp metadata: store both `timestamp_sec` (float) and `timestamp_str` (HH:MM:SS)
- ✅ Parent-child: yes, full lecture = parent, per-frame = child with `context_window` adjacency
- ✅ Math handling: pix2tex fallback triggered by LaTeX density heuristic

### Still Open

**1. Speech transcription integration**
Whisper (via `whisper.cpp` or `faster-whisper`) can produce a timestamped transcript that aligns with extracted frames. A future `--with-transcript` flag could merge speech and visual content into richer chunks:
```
[00:25:23] [Slide: "The Central Limit Theorem"]
[Transcript]: "So what this means is that regardless of the underlying distribution..."
```

**2. YouTube / URL ingestion**
`yt-dlp` can download YouTube videos to a temp file, after which the existing pipeline handles them identically. A `corpus video ingest <youtube_url>` UX is a natural extension:
```bash
corpus video ingest "https://youtube.com/watch?v=..." --collection ocw_mit
```

**3. Schema version tracking**
The video metadata schema should carry a `schema_version` field so future migrations can detect and re-ingest stale chunks without full collection deletion.

**4. Batch ingest**
For full course ingestion (e.g., 30 lecture videos), a `corpus video ingest-dir ./lectures/ --collection cs6301` command that processes all video files in a directory sequentially would save significant manual effort.
