"""
Image preprocessing for handwritten document OCR.

Handles upscaling, denoise, contrast enhancement, and TIFF normalization.
"""

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

    Applies upscaling (when width < target_width), denoise, and contrast enhancement.
    TIFF/TIF inputs are always normalized to JPEG.

    Returns path to preprocessed image. If no preprocessing is needed,
    returns original path unchanged.

    Args:
        image_path: Path to the input image.
        target_width: Target width for upscaling. If img.width < target_width,
                      upscale using LANCZOS while preserving aspect ratio.
        enhance_contrast: If True, apply 1.5x contrast enhancement.
        denoise: If True, apply median filter (size=3) to reduce artifacts.

    Returns:
        Path to the preprocessed image (either original or newly written).
        If no modifications were applied, returns image_path unchanged.
    """
    img = Image.open(image_path).convert("RGB")
    modified = False

    # TIFF normalization: always re-save TIFF files as JPEG
    if image_path.suffix.lower() in {".tif", ".tiff"}:
        modified = True

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

    # For TIFF files, output as JPEG; for other formats, preserve extension
    if image_path.suffix.lower() in {".tif", ".tiff"}:
        out_path = image_path.with_stem(image_path.stem + "_processed").with_suffix(".jpg")
    else:
        out_path = image_path.with_stem(image_path.stem + "_processed")
    img.save(out_path, "JPEG", quality=92)
    return out_path


def is_likely_blank(image_path: Path, blank_threshold: float = 0.02) -> bool:
    """
    Detect blank or near-blank pages to skip.

    Uses edge density as a proxy for content presence.
    Converts image to grayscale, computes mean absolute first-difference
    along both axes, and checks if edge_density < threshold.

    Edge density = (|diff_x|.mean() + |diff_y|.mean()) / 255

    Args:
        image_path: Path to the image file.
        blank_threshold: Edge density threshold. Default 0.02.
                        Pages with edge_density < threshold are considered blank.

    Returns:
        True if page is likely blank, False otherwise.
    """
    img = Image.open(image_path).convert("L")
    arr = np.array(img, dtype=np.float32)

    # Compute mean absolute first-differences along both axes
    diff_x = np.abs(np.diff(arr, axis=1)).mean()
    diff_y = np.abs(np.diff(arr, axis=0)).mean()

    edge_density = (diff_x + diff_y) / 255.0

    return bool(edge_density < blank_threshold)
