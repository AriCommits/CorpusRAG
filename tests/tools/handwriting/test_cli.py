"""Tests for the handwriting ingestion CLI."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

import pytest
from click.testing import CliRunner
from PIL import Image, ImageDraw

# Ensure src/ is on the path (mirrors editable install)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.tools.handwriting.cli import handwriting
from src.tools.handwriting.ingest_handwriting import HandwritingIngestResult


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def tmp_image_dir(tmp_path):
    """Create a temporary directory with synthetic test images."""
    # Create folder structure
    (tmp_path / "2024" / "notes").mkdir(parents=True, exist_ok=True)

    # Create a test image
    def create_image(path, filename):
        img = Image.new("RGB", (200, 200), color="white")
        draw = ImageDraw.Draw(img)
        # Draw some content so it's not detected as blank
        draw.rectangle([10, 10, 50, 50], outline="black", width=2)
        draw.text((60, 60), "Test", fill="black")
        img.save(path / filename, "JPEG")
        return path / filename

    create_image(tmp_path / "2024" / "notes", "page_001.jpg")
    return tmp_path


class TestHandwritingCLI:
    """Tests for the handwriting CLI group and ingest command."""

    def test_help_shows_ingest_command(self, runner: CliRunner) -> None:
        """Verify 'corpus handwriting --help' lists 'ingest' command."""
        result = runner.invoke(handwriting, ["--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output

    def test_ingest_help(self, runner: CliRunner) -> None:
        """Verify 'corpus handwriting ingest --help' shows all flags."""
        result = runner.invoke(handwriting, ["ingest", "--help"])
        assert result.exit_code == 0
        # Check for key flags
        assert "--collection" in result.output
        assert "--recursive" in result.output
        assert "--vision-model" in result.output
        assert "--correction-model" in result.output
        assert "--no-autocorrect" in result.output
        assert "--tags" in result.output
        assert "--context-window" in result.output
        assert "--keep-preprocessed" in result.output
        assert "--max-depth" in result.output

    def test_ingest_with_default_collection(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with default collection='notes'."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            # Verify ingest_handwriting was called with correct collection
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["collection"] == "notes"

    def test_ingest_with_custom_collection(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with custom collection name."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="journal",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--collection", "journal"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["collection"] == "journal"

    def test_ingest_with_no_recursive(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with --no-recursive flag."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=0,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=0,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--no-recursive"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["recursive"] is False

    def test_ingest_with_recursive(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with --recursive flag (default)."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--recursive"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["recursive"] is True

    def test_ingest_with_no_autocorrect(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with --no-autocorrect flag."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--no-autocorrect"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["autocorrect"] is False

    def test_ingest_with_autocorrect_default(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test that autocorrect defaults to True."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["autocorrect"] is True

    def test_ingest_with_keep_preprocessed(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with --keep-preprocessed flag."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--keep-preprocessed"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["cleanup_preprocessed"] is False

    def test_ingest_with_cleanup_preprocessed_default(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test that cleanup_preprocessed defaults to True."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["cleanup_preprocessed"] is True

    def test_ingest_with_single_tag(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with single -t tag flag."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "-t", "Year/2024"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["user_tags"] == ["Year/2024"]

    def test_ingest_with_multiple_tags(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with multiple -t tag flags."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "-t", "Year/2024", "-t", "Domain/Engineering"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["user_tags"] == ["Year/2024", "Domain/Engineering"]

    def test_ingest_with_no_tags(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with no tags (should be None)."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["user_tags"] is None

    def test_ingest_with_context_window(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with custom --context-window."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=1,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=1,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--context-window", "3"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["context_window"] == 3

    def test_ingest_with_max_depth(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test ingest with --max-depth flag."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=0,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=0,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir), "--max-depth", "2"]
            )

            assert result.exit_code == 0
            mock_ingest.assert_called_once()
            call_kwargs = mock_ingest.call_args[1]
            assert call_kwargs["max_depth"] == 2

    def test_ingest_output_summary(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test that ingest prints correct summary output."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=10,
                skipped_already_ingested=2,
                skipped_blank=1,
                pages_ingested=7,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            assert "Ingest complete" in result.output
            assert "Total images found:       10" in result.output
            assert "Already ingested (skip):  2" in result.output
            assert "Blank pages (skip):       1" in result.output
            assert "Pages ingested:           7" in result.output

    def test_ingest_output_with_low_confidence_warning(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test output includes low-confidence warning."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=10,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=9,
                low_confidence_pages=3,
                collection="notes",
                warnings_file=None,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            assert "Low confidence pages:  3" in result.output

    def test_ingest_output_with_failed_pages(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test output includes failed pages warning."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=10,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=8,
                low_confidence_pages=0,
                collection="notes",
                warnings_file=None,
                failed_pages=2,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            assert "Failed pages:           2" in result.output

    def test_ingest_output_with_warnings_file(self, runner: CliRunner, tmp_image_dir) -> None:
        """Test output includes warnings file path."""
        with patch("src.tools.handwriting.cli.load_cli_db") as mock_load_db, \
             patch("src.tools.handwriting.cli.ingest_handwriting") as mock_ingest, \
             patch("src.tools.handwriting.cli.RAGAgent") as mock_agent_class:

            mock_agent_class.return_value = MagicMock()
            mock_load_db.return_value = (MagicMock(), MagicMock())

            warnings_path = str(tmp_image_dir / ".handwriting_warnings.md")
            result_obj = HandwritingIngestResult(
                root_directory=str(tmp_image_dir),
                total_images_found=10,
                skipped_already_ingested=0,
                skipped_blank=0,
                pages_ingested=9,
                low_confidence_pages=2,
                collection="notes",
                warnings_file=warnings_path,
                failed_pages=0,
            )
            mock_ingest.return_value = result_obj

            result = runner.invoke(
                handwriting,
                ["ingest", str(tmp_image_dir)]
            )

            assert result.exit_code == 0
            assert "Warnings file:" in result.output
            assert warnings_path in result.output
