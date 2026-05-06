"""Pipeline orchestrator for handwritten document batch ingestion."""

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


@dataclass(frozen=True)
class HandwritingIngestResult:
    """Result of a handwriting ingestion pipeline run."""

    root_directory: str
    total_images_found: int
    skipped_already_ingested: int
    skipped_blank: int
    pages_ingested: int
    low_confidence_pages: int  # Pages with correction_confidence < threshold
    collection: str
    warnings_file: str | None = None  # Path to .handwriting_warnings.md if written
    failed_pages: int = 0  # Number of pages that failed OCR/correction


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
    user_tags: list[str] | None = None,
    cleanup_preprocessed: bool = True,
    max_depth: int | None = None,
) -> HandwritingIngestResult:
    """
    Full batch handwriting ingestion pipeline.

    Recursively walks root_dir, preprocesses images, runs OCR via vision model,
    applies automatic LLM correction, groups pages by folder, and ingests into
    ChromaDB via agent.ingest_text(). Deduplicates by file hash before processing.

    Args:
        root_dir: Root directory of scanned images.
        collection: Target ChromaDB collection name.
        agent: Initialized CorpusRAG Agent instance with ingest_text() method.
               Optional: agent.get_ingested_hashes(collection) should return set
               of already-ingested SHA-256 hashes. Falls back to set() if missing.
        recursive: Whether to descend into subdirectories.
        vision_model: Ollama vision model for OCR pass (default: "llava").
        correction_model: Ollama text model for correction pass (default: "mistral").
        autocorrect: Whether to run the LLM correction pass (default: True).
        low_confidence_threshold: Flag pages below this correction confidence
                                  (default: 0.75, range [0.0, 1.0]).
        context_window: Adjacent pages to include per child chunk
                       (default: 1 = ±1 neighbor pages).
        user_tags: Tags to inject into all ingested pages metadata (default: None).
        cleanup_preprocessed: Delete preprocessed temp images after ingest
                             (default: True).
        max_depth: Maximum directory depth to traverse. None = unlimited.
                  0 = root only, 1 = root + 1 level, etc.

    Returns:
        HandwritingIngestResult with counts and optional warnings file path.

    Notes:
        - Pages are grouped by folder hierarchy (folder_key = "/".join(folder_hierarchy))
        - Parent docs: one per folder, doc_id="handwriting:{collection}:{folder_key}",
          content concatenated from all pages, metadata with source_type, folder_key, page_count.
        - Child chunks: one per non-blank page, metadata includes parent_id.
        - Per-page errors (OCR/correction failure) are logged and continued.
        - Low-confidence pages trigger a .handwriting_warnings.md file at root_dir.
        - agent.get_ingested_hashes() is optional; if missing, all images are processed.
    """
    root_dir = Path(root_dir)
    logger.info(f"Starting handwriting ingest: {root_dir}")

    # Step 1: Walk directory
    images = walk_directory(root_dir, recursive=recursive, max_depth=max_depth)
    logger.info(f"Found {len(images)} images")

    # Filter already ingested by hash
    # Try to call agent.get_ingested_hashes() if it exists; fall back to empty set
    ingested_hashes = set()
    get_hashes_method = getattr(agent, "get_ingested_hashes", None)
    if callable(get_hashes_method):
        try:
            ingested_hashes = get_hashes_method(collection)
        except Exception as e:
            logger.warning(f"Failed to get ingested hashes from agent: {e}")
            ingested_hashes = set()

    images, skipped_dedup = filter_already_ingested(images, ingested_hashes)
    if skipped_dedup > 0:
        logger.info(f"Skipping {skipped_dedup} already ingested. Processing {len(images)} new.")

    processed_pages = []
    skipped_blank = 0
    low_confidence_count = 0
    failed_pages_count = 0
    preprocessed_paths = []
    low_confidence_pages = []  # Track for warnings file

    for i, image in enumerate(images):
        logger.info(f"[{i+1}/{len(images)}] Processing {image.relative_path}")

        # Step 2: Preprocess image
        try:
            processed_path = preprocess_image(image.path)
            if processed_path != image.path:
                preprocessed_paths.append(processed_path)
        except Exception as e:
            logger.error(f"Failed to preprocess {image.relative_path}: {e}")
            failed_pages_count += 1
            continue

        # Quick blank page check
        try:
            if is_likely_blank(processed_path):
                skipped_blank += 1
                logger.debug(f"Skipping blank page (edge density): {image.relative_path}")
                continue
        except Exception as e:
            logger.error(f"Failed to check if blank {image.relative_path}: {e}")
            failed_pages_count += 1
            continue

        # Steps 3-4: Vision OCR + LLM Correction (wrapped in try/except per-page)
        try:
            raw_text = ocr_handwriting(processed_path, model=vision_model)

            # Check if OCR detected blank page
            if raw_text.strip() == "[BLANK_PAGE]":
                skipped_blank += 1
                logger.debug(f"Skipping blank page (OCR detected): {image.relative_path}")
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
                # Track for warnings file
                low_confidence_pages.append((image.relative_path, confidence))

            # Step 5: Build processed page
            page = build_page(image, corrected_text, confidence, user_tags)
            processed_pages.append(page)

        except Exception as e:
            logger.error(
                f"Failed OCR/correction for {image.relative_path}: {e}",
                exc_info=False
            )
            failed_pages_count += 1
            continue

    logger.info(f"Processed {len(processed_pages)} pages successfully")

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

    logger.info(f"Ingested {len(processed_pages)} pages across {len(folder_groups)} folders")

    # Step 8: Write low-confidence warnings file if needed
    warnings_file = None
    if low_confidence_count > 0:
        warnings_file = str(root_dir / ".handwriting_warnings.md")
        try:
            with open(warnings_file, "w") as f:
                f.write("# Handwriting Ingestion Low-Confidence Pages\n\n")
                f.write(f"Found {low_confidence_count} pages with correction confidence < {low_confidence_threshold}\n\n")
                for relative_path, confidence in low_confidence_pages:
                    f.write(f"- {relative_path} (confidence: {confidence:.2f})\n")
            logger.info(f"Wrote low-confidence warnings to {warnings_file}")
        except Exception as e:
            logger.error(f"Failed to write warnings file {warnings_file}: {e}")
            warnings_file = None

    # Step 9: Cleanup preprocessed temp images
    if cleanup_preprocessed:
        for p in preprocessed_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete preprocessed file {p}: {e}")

    return HandwritingIngestResult(
        root_directory=str(root_dir),
        total_images_found=len(images) + skipped_dedup,
        skipped_already_ingested=skipped_dedup,
        skipped_blank=skipped_blank,
        pages_ingested=len(processed_pages),
        low_confidence_pages=low_confidence_count,
        collection=collection,
        warnings_file=warnings_file,
        failed_pages=failed_pages_count,
    )
