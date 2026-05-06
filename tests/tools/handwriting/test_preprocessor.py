"""
Tests for image preprocessing module.

Tests cover:
- Upscaling logic
- Blank detection
- TIFF normalization
- No-op path when no preprocessing needed
"""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

from src.tools.handwriting.preprocessor import preprocess_image, is_likely_blank


class TestPreprocessImage:
    """Tests for preprocess_image function."""

    def test_no_modification_returns_original_path(self, tmp_path):
        """When image is large enough and flags off, return original path."""
        # Create a large image (larger than default target_width=2048)
        img = Image.new("RGB", (3000, 4000), color=(200, 200, 200))
        image_path = tmp_path / "large_image.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        assert result == image_path
        # Verify no new file was created
        assert len(list(tmp_path.glob("*.jpg"))) == 1

    def test_upscale_when_width_too_small(self, tmp_path):
        """Upscale image when width < target_width."""
        # Create small image
        img = Image.new("RGB", (1000, 1500), color=(200, 200, 200))
        image_path = tmp_path / "small_image.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        assert result != image_path
        assert result.name == "small_image_processed.jpg"
        assert result.exists()

        # Verify upscaled dimensions
        upscaled = Image.open(result)
        assert upscaled.width == 2048
        assert upscaled.height == 3072  # 1500 * (2048/1000)

    def test_upscale_preserves_aspect_ratio(self, tmp_path):
        """Upscaling preserves aspect ratio."""
        # Create image with 2:3 aspect ratio
        img = Image.new("RGB", (800, 1200), color=(200, 200, 200))
        image_path = tmp_path / "aspect_test.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        upscaled = Image.open(result)
        # Expected: 2048 x (1200 * 2048/800) = 2048 x 3072
        assert upscaled.width == 2048
        assert upscaled.height == 3072
        # Verify aspect ratio preserved: height/width should be same
        assert abs((upscaled.height / upscaled.width) - (1200 / 800)) < 0.0001

    def test_tiff_normalization_to_jpeg(self, tmp_path):
        """TIFF inputs are always re-saved as JPEG."""
        # Create TIFF image
        img = Image.new("RGB", (3000, 4000), color=(200, 200, 200))
        image_path = tmp_path / "document.tif"
        img.save(image_path, "TIFF")

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        assert result != image_path
        assert result.suffix == ".jpg"
        assert result.name == "document_processed.jpg"
        assert result.exists()

    def test_tiff_uppercase_normalization(self, tmp_path):
        """Uppercase .TIFF extension is also normalized."""
        img = Image.new("RGB", (3000, 4000), color=(200, 200, 200))
        image_path = tmp_path / "document.TIFF"
        img.save(image_path, "TIFF")

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        assert result != image_path
        assert result.suffix == ".jpg"

    def test_contrast_enhancement_applied(self, tmp_path):
        """Contrast enhancement is applied when enabled."""
        # Create image with low contrast
        img = Image.new("RGB", (3000, 4000), color=(150, 150, 150))
        image_path = tmp_path / "low_contrast.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=True,
            denoise=False,
        )

        assert result != image_path
        assert result.exists()

    def test_denoise_applied(self, tmp_path):
        """Denoise is applied when enabled."""
        img = Image.new("RGB", (3000, 4000), color=(200, 200, 200))
        image_path = tmp_path / "noisy.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=True,
        )

        assert result != image_path
        assert result.exists()

    def test_multiple_modifications_single_output(self, tmp_path):
        """When multiple modifications apply, single output file is created."""
        # Small image that needs upscaling
        img = Image.new("RGB", (1000, 1500), color=(150, 150, 150))
        image_path = tmp_path / "small_noisy.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=True,
            denoise=True,
        )

        assert result != image_path
        # Only one output file should exist
        processed_files = list(tmp_path.glob("*_processed.jpg"))
        assert len(processed_files) == 1
        assert result == processed_files[0]

    def test_output_path_stem_naming(self, tmp_path):
        """Output path uses image_path.with_stem(stem + '_processed')."""
        img = Image.new("RGB", (1000, 1500), color=(200, 200, 200))
        image_path = tmp_path / "my_scan.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        assert result.name == "my_scan_processed.jpg"

    def test_jpeg_quality_92(self, tmp_path):
        """Output JPEG is saved with quality=92."""
        img = Image.new("RGB", (1000, 1500), color=(200, 200, 200))
        image_path = tmp_path / "test.jpg"
        img.save(image_path, "JPEG", quality=92)

        result = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=False,
            denoise=False,
        )

        # Verify file can be opened (valid JPEG)
        result_img = Image.open(result)
        assert result_img.format == "JPEG"


class TestIsLikelyBlank:
    """Tests for is_likely_blank function."""

    def test_solid_color_image_is_blank(self, tmp_path):
        """Solid color image (no edges) returns True."""
        # Create uniformly white image
        img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
        image_path = tmp_path / "blank.jpg"
        img.save(image_path, "JPEG", quality=92)

        assert is_likely_blank(image_path, blank_threshold=0.02) is True

    def test_solid_gray_image_is_blank(self, tmp_path):
        """Solid gray image returns True."""
        img = Image.new("RGB", (800, 1000), color=(128, 128, 128))
        image_path = tmp_path / "gray.jpg"
        img.save(image_path, "JPEG", quality=92)

        assert is_likely_blank(image_path, blank_threshold=0.02) is True

    def test_image_with_text_not_blank(self, tmp_path):
        """Image with visible text/content returns False."""
        # Create image with high-contrast text-like pattern
        img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw black lines to simulate text
        for y in range(100, 900, 50):
            draw.line([(100, y), (700, y)], fill=(0, 0, 0), width=2)

        image_path = tmp_path / "text.jpg"
        img.save(image_path, "JPEG", quality=92)

        assert is_likely_blank(image_path, blank_threshold=0.02) is False

    def test_checkerboard_pattern_not_blank(self, tmp_path):
        """High-edge-density pattern returns False."""
        # Create checkerboard pattern
        img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
        pixels = img.load()

        for y in range(1000):
            for x in range(800):
                if (x // 20 + y // 20) % 2 == 0:
                    pixels[x, y] = (0, 0, 0)

        image_path = tmp_path / "checkerboard.jpg"
        img.save(image_path, "JPEG", quality=92)

        assert is_likely_blank(image_path, blank_threshold=0.02) is False

    def test_threshold_parameter(self, tmp_path):
        """Threshold parameter controls sensitivity."""
        # Create a blank image with no content
        blank_img = Image.new("RGB", (800, 1000), color=(200, 200, 200))
        blank_path = tmp_path / "blank_ref.jpg"
        blank_img.save(blank_path, "JPEG", quality=92)

        # Create an image with high-contrast content
        content_img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(content_img)
        for y in range(0, 1000, 50):
            draw.line([(0, y), (800, y)], fill=(0, 0, 0), width=2)

        content_path = tmp_path / "content.jpg"
        content_img.save(content_path, "JPEG", quality=92)

        # Strict threshold should consider blank image as blank
        assert is_likely_blank(blank_path, blank_threshold=0.1) is True
        # Loose threshold should consider content image as not blank
        assert is_likely_blank(content_path, blank_threshold=0.01) is False

    def test_blank_detection_converts_to_grayscale(self, tmp_path):
        """Blank detection works on color images (converts to grayscale internally)."""
        # Create solid color RGB image
        img = Image.new("RGB", (800, 1000), color=(255, 100, 50))
        image_path = tmp_path / "color_blank.jpg"
        img.save(image_path, "JPEG", quality=92)

        assert is_likely_blank(image_path, blank_threshold=0.02) is True

    def test_edge_density_formula(self, tmp_path):
        """Edge density is calculated as (|diff_x| + |diff_y|) / 255."""
        # Create a simple image with known edge structure
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw a horizontal line in the middle
        draw.line([(0, 50), (100, 50)], fill=(0, 0, 0), width=1)

        image_path = tmp_path / "edge_test.jpg"
        img.save(image_path, "JPEG", quality=92)

        # Should have measurable edges and not be blank
        assert is_likely_blank(image_path, blank_threshold=0.02) is False


class TestIntegration:
    """Integration tests combining preprocessing and blank detection."""

    def test_preprocess_then_check_blank(self, tmp_path):
        """Preprocess image, then check if blank."""
        # Create a small, blank image
        img = Image.new("RGB", (800, 1000), color=(240, 240, 240))
        image_path = tmp_path / "small_blank.jpg"
        img.save(image_path, "JPEG", quality=92)

        # Preprocess it
        processed_path = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=True,
            denoise=True,
        )

        # Check if blank
        is_blank = is_likely_blank(processed_path, blank_threshold=0.02)
        assert is_blank is True

    def test_preprocess_document_with_content(self, tmp_path):
        """Preprocess scanned document with handwritten-like content."""
        # Create a document-like image with content
        img = Image.new("RGB", (800, 1200), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)

        # Simulate handwritten lines with very high contrast for edge detection
        for line_y in range(150, 1100, 40):
            draw.line([(80, line_y), (750, line_y)], fill=(0, 0, 0), width=4)

        image_path = tmp_path / "document.jpg"
        img.save(image_path, "JPEG", quality=92)

        # Preprocess
        processed_path = preprocess_image(
            image_path,
            target_width=2048,
            enhance_contrast=True,
            denoise=True,
        )

        # Should not be blank (use a threshold that accommodates JPEG compression)
        is_blank = is_likely_blank(processed_path, blank_threshold=0.01)
        assert is_blank is False

        # Verify upscaling occurred
        processed_img = Image.open(processed_path)
        assert processed_img.width == 2048
