# Handwritten Document Batch Ingestion Pipeline — Technical Specification

**Project:** CorpusRAG  
**Feature:** `corpus ingest-handwriting`  
**Status:** Ready for implementation  
**Depends on:** R1 (rename), T1 (hierarchical tag parser), Video Pipeline Spec (sibling feature)

---

## Overview

This pipeline converts batches of handwritten document scans (engineering journals,
lecture notes, lab notebooks, personal archives) into structured, searchable markdown
stored in ChromaDB. The pipeline is fully local, fully automated, and designed for
large archives (hundreds to thousands of images) processed in a single command.

The key distinction from the video pipeline is that input is already a directory of
images — no frame extraction required. The pipeline focuses on:

1. Recursive directory traversal with folder hierarchy preserved as metadata
2. Vision-based OCR tuned for handwriting (not printed text)
3. Automated LLM correction pass to clean OCR errors without manual review
4. Confidence-based flagging for genuinely illegible content
5. Deduplication via SHA-256 so re-running the pipeline never double-ingests

---

## Architecture

```
Input Directory (recursive)
    │
    ▼
┌─────────────────────────┐
│  Directory Walker        │  Recursive glob for images
│                          │  Preserves folder hierarchy in metadata
│                          │  Deduplicates via SHA-256 hash
└──────────┬──────────────┘
           │  Image paths + metadata
           ▼
┌─────────────────────────┐
│  Image Preprocessor      │  Deskew, denoise, contrast enhance
│                          │  Upscale low-resolution images
│                          │  Normalize to standard format (JPEG/PNG)
└──────────┬──────────────┘
           │  Preprocessed images
           ▼
┌─────────────────────────┐
│  Vision OCR (Pass 1)     │  llava via Ollama
│                          │  Handwriting-specific prompt
│                          │  Outputs raw markdown per page
└──────────┬──────────────┘
           │  Raw OCR text
           ▼
┌─────────────────────────┐
│  LLM Correction (Pass 2) │  Local LLM (same Ollama instance)
│                          │  Fixes spelling, misread characters
│                          │  Marks illegible passages
│                          │  Preserves technical terminology
└──────────┬──────────────┘
           │  Corrected markdown
           ▼
┌─────────────────────────┐
│  Post-Processor          │  Deduplication of near-identical pages
│                          │  Timestamp/path metadata attachment
│                          │  Optional user tag injection
└──────────┬──────────────┘
           │  Clean chunks + metadata
           ▼
┌─────────────────────────┐
│  Parent-Child Chunker    │  Folder/document = parent
│                          │  Per-page segments = children
└──────────┬──────────────┘
           │  Structured chunks
           ▼
┌─────────────────────────┐
│  ChromaDB Ingest         │  Reuses existing agent.ingest_text()
│                          │  SHA-256 incremental sync
└─────────────────────────┘
```

---

## Directory Structure

```
src/tools/handwriting/
├── __init__.py
├── ingest_handwriting.py     # Pipeline orchestrator — main entry point
├── walker.py                 # Recursive directory traversal + dedup
├── preprocessor.py           # Image enhancement (deskew, denoise, upscale)
├── ocr.py                    # Vision OCR pass (llava)
├── corrector.py              # LLM correction pass
├── postprocessor.py          # Dedup, metadata attachment, tag injection
├── chunker.py                # Parent-child chunking
└── cli.py                    # Click commands
```

---

## Step 1 — Recursive Directory Walker

### Supported Formats

```python
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
```

JPEG is the recommended format (smaller, faster inference). PNG is supported for
lossless quality. TIFF for archival scanner output.

### Implementation

```python
# walker.py

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscoveredImage:
    path: Path
    relative_path: str        # Relative to the root scan directory
    folder_hierarchy: list[str]  # e.g. ["2020", "january"]
    file_hash: str            # SHA-256 of file contents for dedup
    file_size_bytes: int


def walk_directory(
    root: Path,
    recursive: bool = True,
    extensions: set[str] = SUPPORTED_EXTENSIONS,
) -> list[DiscoveredImage]:
    """
    Walk a directory and return all image files.

    Args:
        root: Root directory to scan.
        recursive: If True, descend into subdirectories.
                   If False, only process top-level files.
        extensions: Set of file extensions to include.

    Returns:
        List of DiscoveredImage, sorted by path for consistent ordering.
    """
    pattern = "**/*" if recursive else "*"
    all_files = [
        p for p in root.glob(pattern)
        if p.is_file() and p.suffix.lower() in extensions
    ]
    all_files.sort()

    results = []
    for path in all_files:
        relative = path.relative_to(root)
        hierarchy = list(relative.parts[:-1])  # folders only, not filename
        file_hash = _hash_file(path)
        results.append(DiscoveredImage(
            path=path,
            relative_path=str(relative),
            folder_hierarchy=hierarchy,
            file_hash=file_hash,
            file_size_bytes=path.stat().st_size,
        ))

    return results


def _hash_file(path: Path) -> str:
    """SHA-256 hash of file contents for deduplication."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def filter_already_ingested(
    images: list[DiscoveredImage],
    ingested_hashes: set[str],
) -> tuple[list[DiscoveredImage], int]:
    """
    Remove images already present in ChromaDB by hash.
    Returns (new_images, skipped_count).
    """
    new = [img for img in images if img.file_hash not in ingested_hashes]
    skipped = len(images) - len(new)
    return new, skipped
```

### Folder Hierarchy as Metadata

The folder structure is preserved as metadata so you can filter searches by
time period, topic, or project:

```
journal_scans/
  2020/
    january/
      page_001.jpg   → folder_hierarchy: ["2020", "january"]
    february/
      page_001.jpg   → folder_hierarchy: ["2020", "february"]
  2021/
    projects/
      circuit_design/
        sketch_01.jpg → folder_hierarchy: ["2021", "projects", "circuit_design"]
```

This lets you run targeted queries later:

```python
# Search only 2021 project notes
{"folder_hierarchy": {"$contains": "2021"}}

# Search only circuit design sketches
{"folder_hierarchy": {"$contains": "circuit_design"}}
```

---

## Step 2 — Image Preprocessor

Handwritten notes benefit significantly from preprocessing before OCR. This step
is optional but improves accuracy on low-quality scans.

```python
# preprocessor.py

from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np


def preprocess_image(
    image_path: Path,
    target_width: int = 2048,
    enhance_contrast: bool = True,
    denoise: bool = True,
) -> Path:
    """
    Preprocess a scanned image for handwriting OCR.

    Returns path to preprocessed image (written to temp dir).
    If no preprocessing is needed, returns original path unchanged.
    """
    img = Image.open(image_path).convert("RGB")
    modified = False

    # Upscale low-resolution images
    if img.width < target_width:
        ratio = target_width / img.width
        new_size = (target_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        modified = True

    # Contrast enhancement — helps with faded ink or pencil
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        modified = True

    # Denoise — reduces scan artifacts without blurring text strokes
    if denoise:
        img = img.filter(ImageFilter.MedianFilter(size=3))
        modified = True

    if not modified:
        return image_path

    out_path = image_path.with_stem(image_path.stem + "_processed")
    img.save(out_path, quality=92)
    return out_path


def is_likely_blank(image_path: Path, blank_threshold: float = 0.02) -> bool:
    """
    Detect blank or near-blank pages to skip.
    Uses edge density as a proxy for content presence.
    """
    img = Image.open(image_path).convert("L")
    arr = np.array(img, dtype=np.float32)
    edges = np.abs(np.diff(arr, axis=1)).mean() + np.abs(np.diff(arr, axis=0)).mean()
    edge_density = edges / 255.0
    return edge_density < blank_threshold
```

---

## Step 3 — Vision OCR (Pass 1)

### Handwriting-Specific Prompt

The prompt is tuned for handwritten content rather than slides or printed text.
It explicitly handles common handwriting OCR failure modes.

```python
# ocr.py

import base64
import ollama
from pathlib import Path

HANDWRITING_PROMPT = """
You are transcribing a handwritten document page to markdown.

Instructions:
- Transcribe ALL visible handwritten text as accurately as possible
- Preserve the logical structure: use # for titles, ## for section headers,
  bullet points for lists, and paragraphs for flowing notes
- For mathematical or technical notation, use LaTeX: inline as $expr$,
  display equations as $$expr$$
- For diagrams, sketches, or drawings: describe them concisely in square
  brackets, e.g. [Diagram: circuit with resistor R1 connected to voltage source]
- For crossed-out text: use ~~strikethrough~~ markdown
- For arrows or connective annotations: describe the relationship in brackets,
  e.g. [Arrow from step 3 pointing to note in margin]
- If a word or phrase is genuinely illegible (not just hard to read),
  mark it as [illegible]
- If the page is blank or contains only doodles with no text, respond
  with exactly: [BLANK_PAGE]
- Do not add any commentary, explanation, or preamble — output only the
  transcribed markdown
"""


def ocr_handwriting(
    image_path: Path,
    model: str = "llava",
) -> str:
    """
    Run handwriting OCR on a single image using a vision model.
    Returns raw transcribed markdown.
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    response = ollama.chat(
        model=model,
        messages=[{
            "role": "user",
            "content": HANDWRITING_PROMPT,
            "images": [image_b64],
        }]
    )
    return response["message"]["content"].strip()
```

---

## Step 4 — LLM Correction Pass (Pass 2)

This is the key step that makes batch processing viable without manual review.
The same local LLM that handles RAG queries also corrects OCR output automatically.

```python
# corrector.py

import ollama

CORRECTION_PROMPT = """
You are correcting handwritten notes that were transcribed by a vision model.
The transcription may contain OCR errors: misread characters, spelling mistakes,
incorrect word boundaries, or garbled technical terms.

Your task:
1. Fix obvious OCR errors and misspellings caused by misread handwriting
2. Preserve intentional abbreviations (e.g. "eq." for equation, "cf." for compare)
3. Preserve domain-specific terminology even if it looks unusual
4. Preserve ALL [illegible] markers — do not guess at illegible content
5. Preserve ALL [Diagram: ...] descriptions unchanged
6. Preserve ALL markdown formatting (headers, bullets, LaTeX)
7. Do NOT add, remove, or reinterpret content — only fix clear transcription errors
8. Return ONLY the corrected markdown with no explanation or commentary

Original transcription:
{raw_text}

Corrected markdown:
"""


def correct_ocr_output(
    raw_text: str,
    model: str = "mistral",  # Text model, not vision — faster than llava for this
) -> str:
    """
    Run LLM correction pass on raw OCR output.

    Uses a text-only model (not vision) since we're working with text now.
    Mistral or llama3 are good defaults — fast and accurate for this task.
    """
    if raw_text.strip() in ("[BLANK_PAGE]", ""):
        return raw_text

    prompt = CORRECTION_PROMPT.format(raw_text=raw_text)

    response = ollama.generate(model=model, prompt=prompt)
    return response["response"].strip()


def estimate_correction_confidence(raw: str, corrected: str) -> float:
    """
    Estimate how much the correction changed the text.
    High change rate = potentially low-quality original OCR.
    Returns a score 0.0 (heavily changed) to 1.0 (unchanged).
    """
    if not raw:
        return 0.0
    raw_words = set(raw.lower().split())
    corrected_words = set(corrected.lower().split())
    if not raw_words:
        return 1.0
    overlap = len(raw_words & corrected_words) / len(raw_words)
    return overlap
```

### Why a Separate Text Model for Correction

The vision model (llava) is slow because it processes images. For the correction
pass, we already have text — so we can use a faster text-only model:

| Model | Speed | Quality for correction |
|-------|-------|----------------------|
| `mistral` (7B) | Fast | Excellent |
| `llama3` (8B) | Fast | Excellent |
| `llava` (7B) | Slow | Overkill for text-only |

Using `mistral` for correction roughly halves total pipeline time vs using
`llava` for both passes.

---

## Step 5 — Post-Processor

```python
# postprocessor.py

import hashlib
from dataclasses import dataclass
from pathlib import Path
from src.tools.handwriting.walker import DiscoveredImage


@dataclass
class ProcessedPage:
    content: str                  # Corrected markdown
    source_image: str             # Original image path
    relative_path: str            # Relative to scan root
    folder_hierarchy: list[str]   # Folder path parts
    file_hash: str                # SHA-256 of source image
    content_hash: str             # SHA-256 of OCR content
    correction_confidence: float  # 0.0-1.0, lower = more corrections made
    is_blank: bool
    user_tags: list[str]          # Tags injected from --tags flag or folder name


def build_page(
    image: DiscoveredImage,
    corrected_text: str,
    correction_confidence: float,
    user_tags: list[str] = None,
) -> ProcessedPage:
    content_hash = hashlib.sha256(corrected_text.encode()).hexdigest()[:16]
    return ProcessedPage(
        content=corrected_text,
        source_image=str(image.path),
        relative_path=image.relative_path,
        folder_hierarchy=image.folder_hierarchy,
        file_hash=image.file_hash,
        content_hash=content_hash,
        correction_confidence=correction_confidence,
        is_blank=corrected_text.strip() == "[BLANK_PAGE]",
        user_tags=user_tags or [],
    )


def build_chromadb_metadata(page: ProcessedPage) -> dict:
    """Build ChromaDB metadata dict for a processed page."""
    return {
        "source_file": page.source_image,
        "source_type": "handwriting",
        "relative_path": page.relative_path,
        "folder_hierarchy": page.folder_hierarchy,
        "folder_depth_0": page.folder_hierarchy[0] if len(page.folder_hierarchy) > 0 else "",
        "folder_depth_1": page.folder_hierarchy[1] if len(page.folder_hierarchy) > 1 else "",
        "folder_depth_2": page.folder_hierarchy[2] if len(page.folder_hierarchy) > 2 else "",
        "file_hash": page.file_hash,
        "content_hash": page.content_hash,
        "correction_confidence": page.correction_confidence,
        "tags": page.user_tags,
        "tag_prefixes": list({t.split("/")[0] for t in page.user_tags if "/" in t}),
    }
```

---

## Step 6 — Parent-Child Chunking

For handwritten archives, the parent-child structure maps naturally to:

- **Parent:** entire folder (e.g., `2020/january/`) — stored in LocalFileStore
- **Child:** individual page — indexed in ChromaDB

This allows queries to retrieve a specific page, while the LLM receives surrounding
pages from the same folder session for context.

```python
# chunker.py

from dataclasses import dataclass
from src.tools.handwriting.postprocessor import ProcessedPage, build_chromadb_metadata


@dataclass
class HandwritingChildChunk:
    content: str
    parent_id: str
    metadata: dict


def build_child_chunks(
    pages: list[ProcessedPage],
    parent_id: str,
    context_window: int = 1,
) -> list[HandwritingChildChunk]:
    """
    Build child chunks with adjacent page context.
    context_window=1 includes the page before and after for continuity.
    """
    chunks = []
    for i, page in enumerate(pages):
        if page.is_blank:
            continue

        start = max(0, i - context_window)
        end = min(len(pages), i + context_window + 1)
        context_pages = [p for p in pages[start:end] if not p.is_blank]
        content_with_context = "\n\n---\n\n".join(p.content for p in context_pages)

        metadata = build_chromadb_metadata(page)
        metadata["parent_id"] = parent_id

        chunks.append(HandwritingChildChunk(
            content=content_with_context,
            parent_id=parent_id,
            metadata=metadata,
        ))
    return chunks
```

---

## Step 7 — Pipeline Orchestrator

```python
# ingest_handwriting.py

import logging
from dataclasses import dataclass
from pathlib import Path

from src.tools.handwriting.walker import walk_directory, filter_already_ingested
from src.tools.handwriting.preprocessor import preprocess_image, is_likely_blank
from src.tools.handwriting.ocr import ocr_handwriting
from src.tools.handwriting.corrector import correct_ocr_output, estimate_correction_confidence
from src.tools.handwriting.postprocessor import build_page
from src.tools.handwriting.chunker import build_child_chunks

logger = logging.getLogger(__name__)


@dataclass
class HandwritingIngestResult:
    root_directory: str
    total_images_found: int
    skipped_already_ingested: int
    skipped_blank: int
    pages_ingested: int
    low_confidence_pages: int   # Pages with correction_confidence < threshold
    collection: str


def ingest_handwriting(
    root_dir: Path,
    collection: str,
    agent,
    recursive: bool = True,
    vision_model: str = "llava",
    correction_model: str = "mistral",
    autocorrect: bool = True,
    low_confidence_threshold: float = 0.75,
    context_window: int = 1,
    user_tags: list[str] = None,
    cleanup_preprocessed: bool = True,
) -> HandwritingIngestResult:
    """
    Full batch handwriting ingestion pipeline.

    Args:
        root_dir: Root directory of scanned images.
        collection: Target ChromaDB collection.
        agent: Initialized CorpusRAG Agent instance.
        recursive: Whether to descend into subdirectories.
        vision_model: Ollama vision model for OCR pass.
        correction_model: Ollama text model for correction pass.
        autocorrect: Whether to run the LLM correction pass.
        low_confidence_threshold: Flag pages below this correction confidence.
        context_window: Adjacent pages to include per child chunk.
        user_tags: Tags to inject into all ingested pages metadata.
        cleanup_preprocessed: Delete preprocessed temp images after ingest.
    """
    logger.info(f"Starting handwriting ingest: {root_dir}")

    # Step 1: Walk directory
    images = walk_directory(root_dir, recursive=recursive)
    logger.info(f"Found {len(images)} images")

    # Filter already ingested
    ingested_hashes = agent.get_ingested_hashes(collection)
    images, skipped_dedup = filter_already_ingested(images, ingested_hashes)
    logger.info(f"Skipping {skipped_dedup} already ingested. Processing {len(images)} new.")

    processed_pages = []
    skipped_blank = 0
    low_confidence_count = 0
    preprocessed_paths = []

    for i, image in enumerate(images):
        logger.info(f"[{i+1}/{len(images)}] Processing {image.relative_path}")

        # Step 2: Preprocess
        processed_path = preprocess_image(image.path)
        if processed_path != image.path:
            preprocessed_paths.append(processed_path)

        # Quick blank page check
        if is_likely_blank(processed_path):
            skipped_blank += 1
            logger.debug(f"Skipping blank page: {image.relative_path}")
            continue

        # Step 3: Vision OCR
        raw_text = ocr_handwriting(processed_path, model=vision_model)

        if raw_text.strip() == "[BLANK_PAGE]":
            skipped_blank += 1
            continue

        # Step 4: LLM Correction
        if autocorrect:
            corrected_text = correct_ocr_output(raw_text, model=correction_model)
            confidence = estimate_correction_confidence(raw_text, corrected_text)
        else:
            corrected_text = raw_text
            confidence = 1.0

        if confidence < low_confidence_threshold:
            low_confidence_count += 1
            logger.warning(
                f"Low confidence ({confidence:.2f}) on {image.relative_path} "
                f"— OCR quality may be poor"
            )

        # Step 5: Build processed page
        page = build_page(image, corrected_text, confidence, user_tags)
        processed_pages.append(page)

    # Step 6: Group pages by folder for parent-child structure
    folder_groups: dict[str, list] = {}
    for page in processed_pages:
        folder_key = "/".join(page.folder_hierarchy) or "root"
        folder_groups.setdefault(folder_key, []).append(page)

    # Step 7: Ingest each folder group
    for folder_key, pages in folder_groups.items():
        parent_id = f"handwriting:{collection}:{folder_key}"
        parent_content = "\n\n---\n\n".join(p.content for p in pages)

        # Ingest parent doc
        agent.ingest_text(
            text=parent_content,
            collection=collection,
            doc_id=parent_id,
            metadata={
                "source_type": "handwriting",
                "folder_key": folder_key,
                "page_count": len(pages),
            }
        )

        # Ingest child chunks
        children = build_child_chunks(pages, parent_id, context_window)
        for child in children:
            agent.ingest_text(
                text=child.content,
                collection=collection,
                metadata=child.metadata,
            )

    # Cleanup preprocessed temp images
    if cleanup_preprocessed:
        for p in preprocessed_paths:
            p.unlink(missing_ok=True)

    return HandwritingIngestResult(
        root_directory=str(root_dir),
        total_images_found=len(images) + skipped_dedup,
        skipped_already_ingested=skipped_dedup,
        skipped_blank=skipped_blank,
        pages_ingested=len(processed_pages),
        low_confidence_pages=low_confidence_count,
        collection=collection,
    )
```

---

## Step 8 — CLI Integration

```python
# tools/handwriting/cli.py

import click
from pathlib import Path
from src.tools.handwriting.ingest_handwriting import ingest_handwriting
from corpus_rag.agent import Agent
from corpus_rag.config import load_config


@click.group()
def handwriting():
    """Handwritten document ingestion tools."""
    pass


@handwriting.command("ingest")
@click.argument("directory", type=click.Path(exists=True, path_type=Path))
@click.option("--collection", "-c", default="notes", show_default=True,
              help="Target ChromaDB collection name.")
@click.option("--recursive/--no-recursive", default=True, show_default=True,
              help="Recursively scan subdirectories.")
@click.option("--vision-model", default="llava", show_default=True,
              help="Ollama vision model for OCR.")
@click.option("--correction-model", default="mistral", show_default=True,
              help="Ollama text model for correction pass.")
@click.option("--no-autocorrect", is_flag=True, default=False,
              help="Skip LLM correction pass (faster, less accurate).")
@click.option("--tags", "-t", multiple=True,
              help="Tags to apply to all ingested pages. Can be repeated.")
@click.option("--context-window", default=1, show_default=True,
              help="Adjacent pages to include per chunk.")
@click.option("--keep-preprocessed", is_flag=True, default=False,
              help="Keep preprocessed images after ingest (for debugging).")
def ingest_cmd(
    directory, collection, recursive, vision_model, correction_model,
    no_autocorrect, tags, context_window, keep_preprocessed
):
    """
    Batch ingest a directory of handwritten document scans.

    Recursively walks DIRECTORY, OCRs each image, runs automatic
    correction, and stores searchable markdown in ChromaDB.

    Examples:

      corpus handwriting ingest ./journal_scans/ --collection journal

      corpus handwriting ingest ./notes/2024/ --collection notes --tags "#Year/2024"

      corpus handwriting ingest ./engineering/ --collection eng \\
          --vision-model llava:13b --correction-model mistral

      corpus handwriting ingest ./archive/ --collection archive --no-recursive
    """
    config = load_config()
    agent = Agent(config)

    click.echo(f"Scanning: {directory}")
    click.echo(f"Recursive: {recursive} | Collection: {collection}")
    click.echo(f"Vision model: {vision_model} | Correction model: {correction_model}")
    if tags:
        click.echo(f"Tags: {', '.join(tags)}")

    result = ingest_handwriting(
        root_dir=directory,
        collection=collection,
        agent=agent,
        recursive=recursive,
        vision_model=vision_model,
        correction_model=correction_model,
        autocorrect=not no_autocorrect,
        user_tags=list(tags),
        context_window=context_window,
        cleanup_preprocessed=not keep_preprocessed,
    )

    click.echo(f"\n✓ Ingest complete")
    click.echo(f"  Total images found:       {result.total_images_found}")
    click.echo(f"  Already ingested (skip):  {result.skipped_already_ingested}")
    click.echo(f"  Blank pages (skip):       {result.skipped_blank}")
    click.echo(f"  Pages ingested:           {result.pages_ingested}")
    if result.low_confidence_pages > 0:
        click.echo(
            f"  ⚠ Low confidence pages:  {result.low_confidence_pages} "
            f"(run `corpus handwriting review --collection {collection}` to inspect)"
        )
```

Wire into main CLI:

```python
# src/cli.py
from src.tools.handwriting.cli import handwriting
cli.add_command(handwriting)
```

---

## ChromaDB Metadata Schema

Every child chunk stored in ChromaDB carries:

| Field | Type | Example | Purpose |
|-------|------|---------|---------|
| `source_file` | `str` | `"/scans/2020/jan/page_001.jpg"` | Source image path |
| `source_type` | `str` | `"handwriting"` | Filter handwriting vs other sources |
| `relative_path` | `str` | `"2020/january/page_001.jpg"` | Relative to scan root |
| `folder_hierarchy` | `list[str]` | `["2020", "january"]` | Folder structure for filtering |
| `folder_depth_0` | `str` | `"2020"` | Top-level folder (year, project, etc.) |
| `folder_depth_1` | `str` | `"january"` | Second-level folder |
| `folder_depth_2` | `str` | `""` | Third-level folder |
| `file_hash` | `str` | `"a3f4b2c1..."` | Dedup fingerprint |
| `content_hash` | `str` | `"d9e1f2a3..."` | Content fingerprint |
| `correction_confidence` | `float` | `0.87` | OCR quality indicator |
| `tags` | `list[str]` | `["Year/2020", "Domain/Engineering"]` | User-injected tags |
| `tag_prefixes` | `list[str]` | `["Year", "Domain"]` | Tag subject areas |
| `parent_id` | `str` | `"handwriting:journal:2020/january"` | Link to parent folder doc |

### Example Queries

```python
# All handwriting from 2020
{"folder_depth_0": {"$eq": "2020"}}

# All engineering journal entries
{"folder_hierarchy": {"$contains": "circuit_design"}}

# Low-confidence pages for review
{"$and": [
    {"source_type": {"$eq": "handwriting"}},
    {"correction_confidence": {"$lt": 0.75}},
]}

# Mix handwriting and text in one search (no filter needed)
# Just query normally — all source types share the same collection
```

---

## Recommended Scan Settings

### Phone (Recommended)

Use **Microsoft Lens** or **Adobe Scan** in document mode:

| Setting | Recommendation |
|---------|---------------|
| Format | JPEG |
| Quality | 90% (default) |
| Mode | Document (auto-crop + enhance) |
| Resolution | Native (don't reduce) |
| Color | Grayscale for text-only, Color if diagrams/color coding |

### Dedicated Scanner

| Setting | Recommendation |
|---------|---------------|
| Format | JPEG at 92% or PNG |
| DPI | 300 DPI minimum, 600 DPI for fine handwriting |
| Color | Grayscale for text-only |
| Output | One file per page, auto-numbered |

---

## Dependencies and Installation

```toml
# pyproject.toml

[project.optional-dependencies]
handwriting = [
    "ollama>=0.1.0",
    "Pillow>=10.0.0",
    "numpy>=1.24.0",
]
```

```bash
# Install with handwriting support
pip install corpusrag[handwriting]

# Pull required models
ollama pull llava          # Vision OCR
ollama pull mistral        # Correction pass
```

No system dependencies beyond Ollama itself.

---

## New Dependencies

| Package | Purpose | Optional? |
|---------|---------|-----------|
| `ollama` | Vision OCR + LLM correction | No (core of pipeline) |
| `Pillow` | Image preprocessing | No |
| `numpy` | Blank page detection heuristic | No |

---

## File Change Summary

| File | Action |
|------|--------|
| `src/tools/handwriting/__init__.py` | NEW |
| `src/tools/handwriting/ingest_handwriting.py` | NEW |
| `src/tools/handwriting/walker.py` | NEW |
| `src/tools/handwriting/preprocessor.py` | NEW |
| `src/tools/handwriting/ocr.py` | NEW |
| `src/tools/handwriting/corrector.py` | NEW |
| `src/tools/handwriting/postprocessor.py` | NEW |
| `src/tools/handwriting/chunker.py` | NEW |
| `src/tools/handwriting/cli.py` | NEW |
| `src/cli.py` | Modify — add handwriting command group |
| `pyproject.toml` | Modify — add `[handwriting]` optional extra |
| `README.md` | Modify — document new commands |

---

## Open Questions

1. **Page ordering across folders:** if a journal spans multiple folders (e.g.,
   `2020/january/` and `2020/february/`), should the parent doc include all pages
   chronologically, or stay folder-scoped? Folder-scoped is simpler; chronological
   requires sorting by filename/timestamp.
    - Answer: The transcribed notes should mirror the original structure of the image directory.


2. **Multi-page sequences:** if a single thought or diagram spans pages 5–7, the
   `context_window=1` approach partially handles this but may miss page 7 when
   retrieving page 5. A sliding window or explicit "continued on next page" detection
   would help.
   - maybe we can add some metadata to each file that will support this. we should pre-cacluate how the image will be trasncribed/ how much memory it will require. This way we can also display feedback/statisticcs/metrics regarding the upload. Then the metadata will follow naturally from the callculations based on the context widnow/ some nautral limitation associated with the file.

3. **Low-confidence review command:** the CLI warns about low-confidence pages but
   a `corpus handwriting review --collection journal` command that surfaces these
   pages for optional manual correction would be a high-value follow-up feature.
   - maybe output this as a **warning.md** file that has all the relevant file names.

4. **Image format normalization:** TIFF files from dedicated scanners should be
   converted to JPEG before passing to Ollama — some Ollama builds don't handle
   TIFF directly. Add format normalization to preprocessor.
   - this is fine.

5. **Recursive depth limit:** very deep directory trees could cause issues.
   Add a `--max-depth` flag defaulting to no limit.
   - I am good with this suggestion.
