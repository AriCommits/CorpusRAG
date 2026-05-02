"""Video OCR pipeline orchestrator."""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from utils.security import sanitize_filename

from .classifier import FrameType, classify_frame
from .config import VideoConfig
from .extractor import ExtractedFrame, extract_keyframes
from .ocr import ocr_frame_with_fallback
from .postprocessor import (
    ProcessedChunk,
    build_chunk,
    deduplicate_chunks,
    format_chunk_markdown,
)

logger = logging.getLogger(__name__)


@dataclass
class VideoIngestResult:
    source_file: str
    frames_extracted: int
    frames_skipped: int
    chunks_after_dedup: int
    duration_sec: float
    output_path: Path | None = None
    chunks: list[ProcessedChunk] = field(default_factory=list)


def ingest_video(
    video_path: Path,
    config: VideoConfig,
    output_dir: Path | None = None,
    progress_cb: Callable[[int, str], None] | None = None,
    scene_threshold: float | None = None,
    vision_model: str | None = None,
    use_latex_fallback: bool | None = None,
    dedup_threshold: float | None = None,
    context_window: int | None = None,
    cleanup_frames: bool = True,
) -> VideoIngestResult:
    """Run the full visual OCR pipeline on a video file.

    Returns structured markdown and metadata. Does NOT ingest into ChromaDB
    directly — the caller handles that via RAG ingester or direct DB calls.
    """
    # Resolve config overrides
    threshold = scene_threshold if scene_threshold is not None else config.scene_threshold
    model = vision_model or config.vision_model
    latex = use_latex_fallback if use_latex_fallback is not None else config.use_latex_fallback
    dedup_thresh = dedup_threshold if dedup_threshold is not None else config.dedup_threshold
    ctx_window = context_window if context_window is not None else config.context_window
    endpoint = config.llm.endpoint

    safe_stem = sanitize_filename(video_path.stem) or "unnamed"
    frames_dir = config.paths.scratch_dir / "video_frames" / safe_stem

    def _progress(pct: int, step: str):
        if progress_cb:
            progress_cb(pct, step)

    # Step 1: Extract keyframes (0-20%)
    _progress(0, "Extracting keyframes")
    logger.info("Extracting keyframes from %s (threshold=%.2f)", video_path.name, threshold)
    frames = extract_keyframes(
        video_path, frames_dir, threshold, config.min_frame_interval
    )
    logger.info("Extracted %d frames", len(frames))
    _progress(20, f"Extracted {len(frames)} frames")

    if not frames:
        return VideoIngestResult(
            source_file=str(video_path), frames_extracted=0,
            frames_skipped=0, chunks_after_dedup=0, duration_sec=0,
        )

    # Step 2: Classify frames (20-30%)
    _progress(20, "Classifying frames")
    classified: list[tuple[ExtractedFrame, FrameType]] = []
    skipped = 0
    for frame in frames:
        ft = classify_frame(frame.path)
        if ft == FrameType.NO_CONTENT:
            skipped += 1
        else:
            classified.append((frame, ft))
    logger.info("%d content frames, %d skipped", len(classified), skipped)
    _progress(30, f"{len(classified)} content frames")

    # Step 3: OCR frames (30-80%)
    _progress(30, "Running OCR")
    raw_chunks: list[ProcessedChunk] = []
    total = len(classified)
    for i, (frame, ft) in enumerate(classified):
        text = ocr_frame_with_fallback(
            frame.path, ft, model=model, endpoint=endpoint,
            use_latex_fallback=latex,
        )
        if text != "[NO_CONTENT]":
            raw_chunks.append(build_chunk(text, frame, ft.value, video_path))
        else:
            skipped += 1
        pct = 30 + int(50 * (i + 1) / max(total, 1))
        _progress(pct, f"OCR {i+1}/{total}")

    logger.info("OCR complete: %d chunks", len(raw_chunks))

    # Step 4: Deduplicate (80-90%)
    _progress(80, "Deduplicating")
    chunks = deduplicate_chunks(raw_chunks, dedup_thresh)
    logger.info("After dedup: %d chunks", len(chunks))
    _progress(90, f"{len(chunks)} unique chunks")

    # Step 5: Build output markdown (90-100%)
    _progress(90, "Building output")
    duration = frames[-1].source_timestamp_sec if frames else 0.0

    # Build context-windowed markdown
    sections = []
    for i, chunk in enumerate(chunks):
        start = max(0, i - ctx_window)
        end = min(len(chunks), i + ctx_window + 1)
        context = "\n\n".join(format_chunk_markdown(c) for c in chunks[start:end])
        sections.append(context)

    full_markdown = "\n\n---\n\n".join(
        format_chunk_markdown(c) for c in chunks
    )

    # Write output file if output_dir provided
    output_path = None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}_ocr.md"
        output_path.write_text(full_markdown, encoding="utf-8")
        logger.info("Written to %s", output_path)

    # Cleanup
    if cleanup_frames and frames_dir.exists():
        shutil.rmtree(frames_dir, ignore_errors=True)

    _progress(100, "Complete")

    return VideoIngestResult(
        source_file=str(video_path),
        frames_extracted=len(frames),
        frames_skipped=skipped,
        chunks_after_dedup=len(chunks),
        duration_sec=duration,
        output_path=output_path,
        chunks=chunks,
    )
