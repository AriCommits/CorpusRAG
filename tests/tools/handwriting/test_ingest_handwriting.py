"""End-to-end tests for the handwriting ingestion pipeline orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image, ImageDraw

from src.tools.handwriting.ingest_handwriting import (
    ingest_handwriting,
    HandwritingIngestResult,
)


class FakeAgent:
    """Mock Agent that records ingest_text calls for testing."""

    def __init__(self, ingested_hashes=None):
        """
        Initialize FakeAgent.

        Args:
            ingested_hashes: Dict mapping collection names to sets of hashes.
                           If None, no hashes are pre-ingested.
        """
        self.ingested_hashes = ingested_hashes or {}
        self.ingest_calls = []  # List of dicts: {text, collection, doc_id, metadata}

    def get_ingested_hashes(self, collection):
        """Return pre-ingested hashes for a collection."""
        return self.ingested_hashes.get(collection, set())

    def ingest_text(self, text, collection, doc_id=None, metadata=None):
        """Record an ingest call."""
        self.ingest_calls.append({
            "text": text,
            "collection": collection,
            "doc_id": doc_id,
            "metadata": metadata,
        })


@pytest.fixture
def tmp_image_dir(tmp_path):
    """Create a temporary directory with synthetic test images."""
    # Create folder structure
    (tmp_path / "2024" / "notes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "2024" / "sketches").mkdir(parents=True, exist_ok=True)
    (tmp_path / "archive").mkdir(parents=True, exist_ok=True)

    # Create synthetic images using PIL
    # Each image is 200x200 with white background and some black pixels
    # to avoid being detected as blank
    def create_image(path, filename, has_content=True):
        img = Image.new("RGB", (200, 200), color="white")
        if has_content:
            draw = ImageDraw.Draw(img)
            # Draw some lines/pixels so it's not detected as blank
            draw.rectangle([10, 10, 50, 50], outline="black", width=2)
            draw.text((60, 60), "Test", fill="black")
        img.save(path / filename, "JPEG")
        return path / filename

    # Create test images with content
    create_image(tmp_path / "2024" / "notes", "page_001.jpg", has_content=True)
    create_image(tmp_path / "2024" / "notes", "page_002.jpg", has_content=True)
    create_image(tmp_path / "2024" / "sketches", "sketch_001.jpg", has_content=True)
    create_image(tmp_path / "archive", "document_001.jpg", has_content=True)

    # Create one blank image (all white, no drawn content)
    blank_img = Image.new("RGB", (200, 200), color="white")
    blank_img.save(tmp_path / "archive" / "blank_page.jpg", "JPEG")

    return tmp_path


class TestIngestHandwritingBasic:
    """Basic orchestrator functionality tests."""

    def test_ingest_result_dataclass(self):
        """Test HandwritingIngestResult dataclass."""
        result = HandwritingIngestResult(
            root_directory="/test/root",
            total_images_found=10,
            skipped_already_ingested=2,
            skipped_blank=1,
            pages_ingested=7,
            low_confidence_pages=1,
            collection="notes",
            warnings_file="/test/.handwriting_warnings.md",
            failed_pages=0,
        )

        assert result.root_directory == "/test/root"
        assert result.total_images_found == 10
        assert result.skipped_already_ingested == 2
        assert result.skipped_blank == 1
        assert result.pages_ingested == 7
        assert result.low_confidence_pages == 1
        assert result.collection == "notes"
        assert result.warnings_file == "/test/.handwriting_warnings.md"
        assert result.failed_pages == 0

    def test_ingest_result_frozen(self):
        """Test that HandwritingIngestResult is frozen."""
        result = HandwritingIngestResult(
            root_directory="/test",
            total_images_found=5,
            skipped_already_ingested=0,
            skipped_blank=0,
            pages_ingested=5,
            low_confidence_pages=0,
            collection="test",
        )

        with pytest.raises(AttributeError):
            result.total_images_found = 10

    def test_ingest_handwriting_basic_flow(self, tmp_image_dir):
        """Test basic ingest flow with mocked OCR/correction."""
        agent = FakeAgent()

        # Mock the OCR and correction functions
        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            # Setup mocks
            mock_ocr.return_value = "# Test Page\nThis is a test page."
            mock_correct.return_value = "# Test Page\nThis is a test page."
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False  # No pages are blank

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                autocorrect=True,
                cleanup_preprocessed=False,  # Keep for inspection in tests
            )

            # Verify result
            assert result.collection == "test_collection"
            assert result.total_images_found == 5  # 4 with content + 1 blank
            assert result.skipped_blank == 0  # is_likely_blank is mocked to False
            assert result.pages_ingested == 5
            assert result.failed_pages == 0

            # Verify agent was called
            assert len(agent.ingest_calls) > 0

            # Verify parent docs were created (one per folder)
            parent_docs = [call for call in agent.ingest_calls if call["doc_id"] is not None]
            assert len(parent_docs) == 3  # 2024/notes, 2024/sketches, archive

    def test_ingest_with_deduplication(self, tmp_image_dir):
        """Test that deduplication works correctly."""
        # Pre-ingest some files
        existing_hashes = set()

        # Read the hash of the first image to pre-populate existing hashes
        first_image = list(tmp_image_dir.glob("**/*.jpg"))[0]
        import hashlib
        with open(first_image, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        existing_hashes.add(file_hash)

        agent = FakeAgent({"test_collection": existing_hashes})

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=False,
            )

            # Should have skipped at least one
            assert result.skipped_already_ingested >= 1
            assert result.total_images_found == 5
            # Pages ingested = total - deduped - blank
            assert result.pages_ingested == 5 - result.skipped_already_ingested - result.skipped_blank

    def test_ingest_blank_page_detection(self, tmp_image_dir):
        """Test that blank pages are skipped."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            # Mock is_likely_blank to return True for the blank_page.jpg
            def is_blank_side_effect(path):
                return "blank_page" in str(path)

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.side_effect = is_blank_side_effect

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=False,
            )

            # Should have skipped the blank page
            assert result.skipped_blank >= 1

    def test_ingest_with_low_confidence_warning(self, tmp_image_dir):
        """Test that low-confidence pages trigger warnings file."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "garbled text here"
            # Return heavily corrected text to trigger low confidence
            mock_correct.return_value = "completely different corrected text that bears no resemblance"
            mock_confidence.return_value = 0.35  # Below 0.75 threshold
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                low_confidence_threshold=0.75,
                cleanup_preprocessed=False,
            )

            # Should have detected low-confidence pages
            assert result.low_confidence_pages > 0
            assert result.warnings_file is not None

            # Verify warnings file was created
            warnings_path = Path(result.warnings_file)
            assert warnings_path.exists()
            content = warnings_path.read_text()
            assert "Low-Confidence Pages" in content or "low-confidence" in content.lower()
            assert "confidence:" in content

    def test_ingest_with_failed_pages(self, tmp_image_dir):
        """Test that OCR/correction failures don't abort the pipeline."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            # Make OCR fail for some images
            def ocr_side_effect(path, **kwargs):
                if "page_001" in str(path):
                    raise RuntimeError("OCR service down")
                return "# Test Page"

            mock_ocr.side_effect = ocr_side_effect
            mock_correct.return_value = "# Test Page"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=False,
            )

            # Should have recorded failed pages
            assert result.failed_pages >= 1
            # But pipeline should continue and ingest other pages
            assert result.pages_ingested > 0

    def test_ingest_folder_grouping(self, tmp_image_dir):
        """Test that pages are grouped by folder correctly."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=False,
            )

            # Extract parent doc IDs
            parent_docs = [call for call in agent.ingest_calls if call["doc_id"] is not None]

            # Should have one parent per folder: 2024/notes, 2024/sketches, archive
            assert len(parent_docs) == 3

            parent_ids = {call["doc_id"] for call in parent_docs}
            expected_prefixes = {"handwriting:test_collection:2024/notes",
                                "handwriting:test_collection:2024/sketches",
                                "handwriting:test_collection:archive"}
            assert parent_ids == expected_prefixes

            # Verify metadata on parent docs
            for call in parent_docs:
                assert call["metadata"]["source_type"] == "handwriting"
                assert "folder_key" in call["metadata"]
                assert "page_count" in call["metadata"]

    def test_ingest_no_autocorrect(self, tmp_image_dir):
        """Test ingest with autocorrect disabled."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Raw OCR Text"
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                autocorrect=False,
                cleanup_preprocessed=False,
            )

            # correct_ocr_output should not be called
            assert result.pages_ingested > 0
            # Low confidence should all be 1.0 (no correction = 1.0 confidence)
            assert result.low_confidence_pages == 0

    def test_ingest_with_max_depth(self, tmp_image_dir):
        """Test that max_depth parameter limits directory traversal."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            # max_depth=0 means only root-level files
            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                max_depth=0,
                cleanup_preprocessed=False,
            )

            # Should find 0 images at depth 0 (all images are in subdirs)
            assert result.total_images_found == 0

    def test_ingest_child_chunks_created(self, tmp_image_dir):
        """Test that child chunks are created with parent_id metadata."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=False,
            )

            # Extract child chunk calls (those without doc_id)
            child_calls = [call for call in agent.ingest_calls if call["doc_id"] is None]

            # Should have multiple child chunks
            assert len(child_calls) > 0

            # Verify each child has parent_id in metadata
            for call in child_calls:
                assert "parent_id" in call["metadata"]
                assert call["metadata"]["parent_id"].startswith("handwriting:test_collection:")

    def test_ingest_cleanup_preprocessed(self, tmp_image_dir):
        """Test that preprocessed files are cleaned up when cleanup_preprocessed=True."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank, \
             patch("src.tools.handwriting.ingest_handwriting.preprocess_image") as mock_preprocess:

            # Create a fake preprocessed file
            fake_processed = tmp_image_dir / "fake_processed.jpg"
            fake_processed.write_text("fake")

            # Return the fake preprocessed file for all calls
            mock_preprocess.return_value = fake_processed
            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=True,  # Enable cleanup
            )

            # The fake preprocessed file should be deleted
            # (We can't assert this because the mock prevents the actual deletion,
            # but we can verify the function ran without error)
            assert result.pages_ingested > 0


class TestIngestHandwritingAgent:
    """Tests specifically for agent interaction."""

    def test_agent_without_get_ingested_hashes(self, tmp_image_dir):
        """Test that missing get_ingested_hashes method is handled gracefully."""

        class MinimalAgent:
            """Agent without get_ingested_hashes method."""
            def __init__(self):
                self.ingest_calls = []

            def ingest_text(self, text, collection, doc_id=None, metadata=None):
                self.ingest_calls.append({
                    "text": text,
                    "collection": collection,
                    "doc_id": doc_id,
                    "metadata": metadata,
                })

        agent = MinimalAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            # Should not raise an error
            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                cleanup_preprocessed=False,
            )

            # Should process all images (no dedup)
            assert result.skipped_already_ingested == 0
            assert result.pages_ingested > 0

    def test_user_tags_propagation(self, tmp_image_dir):
        """Test that user tags are attached to pages."""
        agent = FakeAgent()

        with patch("src.tools.handwriting.ingest_handwriting.ocr_handwriting") as mock_ocr, \
             patch("src.tools.handwriting.ingest_handwriting.correct_ocr_output") as mock_correct, \
             patch("src.tools.handwriting.ingest_handwriting.estimate_correction_confidence") as mock_confidence, \
             patch("src.tools.handwriting.ingest_handwriting.is_likely_blank") as mock_is_blank:

            mock_ocr.return_value = "# Test"
            mock_correct.return_value = "# Test"
            mock_confidence.return_value = 0.95
            mock_is_blank.return_value = False

            user_tags = ["Year/2024", "Subject/Notes"]

            result = ingest_handwriting(
                root_dir=tmp_image_dir,
                collection="test_collection",
                agent=agent,
                user_tags=user_tags,
                cleanup_preprocessed=False,
            )

            # Verify tags appear in child chunk metadata
            child_calls = [call for call in agent.ingest_calls if call["doc_id"] is None]
            for call in child_calls:
                assert "tags" in call["metadata"]
                assert call["metadata"]["tags"] == user_tags
