"""Tests for file conversion utility."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from corpus_callosum.convert import (
    DEFAULT_OUTPUT_DIR,
    FileConverter,
    format_results_summary,
    format_scan_summary,
)
from corpus_callosum.converters import ConversionResult
from corpus_callosum.converters.docx import DocxConverter
from corpus_callosum.converters.html import HtmlConverter
from corpus_callosum.converters.pdf import PdfConverter
from corpus_callosum.converters.rtf import RtfConverter
from corpus_callosum.converters.txt import TxtConverter


class TestBaseConverter:
    """Tests for BaseConverter ABC."""

    def test_can_convert_matching_extension(self):
        """Test can_convert returns True for matching extensions."""
        converter = TxtConverter()
        assert converter.can_convert(Path("test.txt"))
        assert converter.can_convert(Path("test.TXT"))

    def test_can_convert_non_matching_extension(self):
        """Test can_convert returns False for non-matching extensions."""
        converter = TxtConverter()
        assert not converter.can_convert(Path("test.pdf"))
        assert not converter.can_convert(Path("test.docx"))


class TestTxtConverter:
    """Tests for plain text converter."""

    def test_convert_simple_text(self):
        """Test converting plain text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!\nThis is a test.")
            f.flush()
            path = Path(f.name)

        converter = TxtConverter()
        result = converter.convert(path)

        assert "Hello, World!" in result
        assert "This is a test." in result
        path.unlink()

    def test_convert_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("  \n  Content here  \n  ")
            f.flush()
            path = Path(f.name)

        converter = TxtConverter()
        result = converter.convert(path)

        assert result == "Content here"
        path.unlink()

    def test_extensions(self):
        """Test supported extensions."""
        converter = TxtConverter()
        assert converter.extensions == (".txt",)


class TestPdfConverter:
    """Tests for PDF converter."""

    def test_extensions(self):
        """Test supported extensions."""
        converter = PdfConverter()
        assert converter.extensions == (".pdf",)

    def test_convert_single_page_pdf(self):
        """Test converting a single-page PDF."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)

        # Create a minimal valid PDF
        # Note: PDF xref entries require trailing spaces (20 bytes each)
        pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 100 700 Td (Test content) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f\x20
0000000009 00000 n\x20
0000000058 00000 n\x20
0000000115 00000 n\x20
0000000214 00000 n\x20
trailer << /Size 5 /Root 1 0 R >>
startxref
307
%%EOF"""
        path.write_bytes(pdf_content)

        converter = PdfConverter()
        # The PDF might not extract text properly due to missing font, but shouldn't crash
        try:
            result = converter.convert(path)
            assert isinstance(result, str)
        finally:
            path.unlink()


class TestDocxConverter:
    """Tests for DOCX converter."""

    def test_extensions(self):
        """Test supported extensions."""
        converter = DocxConverter()
        assert converter.extensions == (".docx",)

    def test_convert_with_mock(self):
        """Test DOCX conversion with mocked Document."""
        converter = DocxConverter()

        # Create mock paragraph
        mock_para = MagicMock()
        mock_para.text = "Test paragraph"
        mock_para.style.name = "Normal"

        mock_heading = MagicMock()
        mock_heading.text = "Test Heading"
        mock_heading.style.name = "Heading 1"

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_heading, mock_para]

        with patch("docx.Document", return_value=mock_doc):
            result = converter.convert(Path("test.docx"))

        assert "# Test Heading" in result
        assert "Test paragraph" in result


class TestHtmlConverter:
    """Tests for HTML converter."""

    def test_extensions(self):
        """Test supported extensions."""
        converter = HtmlConverter()
        assert converter.extensions == (".html", ".htm")

    def test_convert_simple_html(self):
        """Test converting simple HTML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("""
            <html>
            <head><title>Test</title></head>
            <body>
                <h1>Main Title</h1>
                <p>This is a paragraph.</p>
            </body>
            </html>
            """)
            f.flush()
            path = Path(f.name)

        converter = HtmlConverter()
        result = converter.convert(path)

        assert "Main Title" in result
        assert "This is a paragraph" in result
        path.unlink()

    def test_removes_script_tags(self):
        """Test that script tags are removed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("""
            <html>
            <body>
                <p>Content</p>
                <script>alert('evil');</script>
            </body>
            </html>
            """)
            f.flush()
            path = Path(f.name)

        converter = HtmlConverter()
        result = converter.convert(path)

        assert "Content" in result
        assert "alert" not in result
        assert "script" not in result.lower()
        path.unlink()

    def test_removes_style_tags(self):
        """Test that style tags are removed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("""
            <html>
            <head><style>body { color: red; }</style></head>
            <body><p>Styled content</p></body>
            </html>
            """)
            f.flush()
            path = Path(f.name)

        converter = HtmlConverter()
        result = converter.convert(path)

        assert "Styled content" in result
        assert "color: red" not in result
        path.unlink()


class TestRtfConverter:
    """Tests for RTF converter."""

    def test_extensions(self):
        """Test supported extensions."""
        converter = RtfConverter()
        assert converter.extensions == (".rtf",)

    def test_convert_simple_rtf(self):
        """Test converting simple RTF content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".rtf", delete=False) as f:
            # Simple RTF with plain text
            f.write(r"{\rtf1\ansi Hello RTF World!}")
            f.flush()
            path = Path(f.name)

        converter = RtfConverter()
        result = converter.convert(path)

        assert "Hello RTF World!" in result
        path.unlink()


class TestFileConverter:
    """Tests for FileConverter orchestration."""

    def test_get_supported_extensions(self):
        """Test getting all supported extensions."""
        converter = FileConverter()
        extensions = converter.get_supported_extensions()

        assert ".txt" in extensions
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".html" in extensions
        assert ".htm" in extensions
        assert ".rtf" in extensions

    def test_get_converter_for_extension(self):
        """Test getting converter for specific extension."""
        converter = FileConverter()

        assert isinstance(converter.get_converter(".txt"), TxtConverter)
        assert isinstance(converter.get_converter(".pdf"), PdfConverter)
        assert isinstance(converter.get_converter(".docx"), DocxConverter)
        assert isinstance(converter.get_converter(".html"), HtmlConverter)
        assert isinstance(converter.get_converter(".rtf"), RtfConverter)
        assert converter.get_converter(".xyz") is None

    def test_scan_directory_groups_by_extension(self):
        """Test that scan_directory groups files by extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test files
            (tmp_path / "file1.txt").write_text("text 1")
            (tmp_path / "file2.txt").write_text("text 2")
            (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4")
            (tmp_path / "image.jpg").write_bytes(b"\xff\xd8\xff")

            converter = FileConverter()
            groups = converter.scan_directory(tmp_path)

            assert ".txt" in groups
            assert len(groups[".txt"]) == 2
            assert ".pdf" in groups
            assert len(groups[".pdf"]) == 1
            assert ".jpg" in groups
            assert len(groups[".jpg"]) == 1

    def test_scan_directory_includes_subdirs(self):
        """Test that scan_directory includes files in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create nested structure
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            (tmp_path / "root.txt").write_text("root")
            (subdir / "nested.txt").write_text("nested")

            converter = FileConverter()
            groups = converter.scan_directory(tmp_path)

            assert ".txt" in groups
            assert len(groups[".txt"]) == 2

    def test_flatten_filename_simple(self):
        """Test flattening a simple filename."""
        converter = FileConverter()
        source_dir = Path("/source")
        file_path = Path("/source/file.pdf")

        result = converter.flatten_filename(source_dir, file_path)
        assert result == "file.md"

    def test_flatten_filename_nested(self):
        """Test flattening a nested filename."""
        converter = FileConverter()
        source_dir = Path("/source")
        file_path = Path("/source/sub/dir/file.pdf")

        result = converter.flatten_filename(source_dir, file_path)
        assert result == "sub_dir_file.md"

    def test_get_convertible_files(self):
        """Test getting only convertible files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            (tmp_path / "doc.txt").write_text("text")
            (tmp_path / "image.jpg").write_bytes(b"\xff\xd8\xff")

            converter = FileConverter()
            convertible = converter.get_convertible_files(tmp_path)

            assert ".txt" in convertible
            assert ".jpg" not in convertible

    def test_get_unconvertible_files(self):
        """Test getting unconvertible files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            (tmp_path / "doc.txt").write_text("text")
            (tmp_path / "image.jpg").write_bytes(b"\xff\xd8\xff")
            (tmp_path / "existing.md").write_text("markdown")

            converter = FileConverter()
            unconvertible = converter.get_unconvertible_files(tmp_path)

            assert ".jpg" in unconvertible
            # .md and .txt should not be in unconvertible
            assert ".txt" not in unconvertible
            assert ".md" not in unconvertible

    def test_convert_file_success(self):
        """Test successful file conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.txt"
            output = tmp_path / "test.md"
            source.write_text("Hello World")

            converter = FileConverter()
            result = converter.convert_file(source, output)

            assert result.success
            assert result.output_path == output
            assert result.error is None
            assert output.exists()
            assert output.read_text() == "Hello World"

    def test_convert_file_unsupported_extension(self):
        """Test conversion failure for unsupported extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.xyz"
            output = tmp_path / "test.md"
            source.write_text("content")

            converter = FileConverter()
            result = converter.convert_file(source, output)

            assert not result.success
            assert result.output_path is None
            assert result.error is not None and "No converter" in result.error

    def test_convert_directory_creates_output_dir(self):
        """Test that convert_directory creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "test.txt").write_text("content")

            converter = FileConverter()
            converter.convert_directory(tmp_path)

            output_dir = tmp_path / DEFAULT_OUTPUT_DIR
            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_convert_directory_flattens_files(self):
        """Test that convert_directory flattens nested files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create nested structure
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            (subdir / "nested.txt").write_text("nested content")

            converter = FileConverter()
            converter.convert_directory(tmp_path)

            output_dir = tmp_path / DEFAULT_OUTPUT_DIR
            # Check flattened name
            assert (output_dir / "subdir_nested.md").exists()

    def test_convert_directory_handles_duplicates(self):
        """Test that convert_directory handles duplicate filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create files that would have same flattened name
            dir1 = tmp_path / "a_b"
            dir2 = tmp_path / "a" / "b"
            dir1.mkdir(parents=True)
            dir2.mkdir(parents=True)
            (dir1 / "file.txt").write_text("content 1")
            (dir2 / "file.txt").write_text("content 2")

            converter = FileConverter()
            results = converter.convert_directory(tmp_path)

            # Both should be converted with unique names
            assert len([r for r in results if r.success]) == 2
            output_dir = tmp_path / DEFAULT_OUTPUT_DIR
            md_files = list(output_dir.glob("*.md"))
            assert len(md_files) == 2

    def test_convert_directory_skips_output_dir_files(self):
        """Test that files in output dir are not re-converted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create a file in the source
            (tmp_path / "source.txt").write_text("source")

            # Run conversion twice
            converter = FileConverter()
            results1 = converter.convert_directory(tmp_path)
            results2 = converter.convert_directory(tmp_path)

            # Second run should not convert the already-converted files
            # (they're in the output dir and would be skipped)
            assert len(results1) == 1
            assert len(results2) == 1  # Only the source.txt again

    def test_convert_directory_continues_on_error(self):
        """Test that conversion continues even if one file fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create valid and "invalid" files
            (tmp_path / "valid.txt").write_text("valid")
            # Create a file that will fail (we'll mock the converter to fail)
            (tmp_path / "other.txt").write_text("other")

            converter = FileConverter()

            # Patch the txt converter to fail on specific file
            original_convert = TxtConverter.convert

            def failing_convert(self, source):
                if "other" in str(source):
                    raise ValueError("Simulated failure")
                return original_convert(self, source)

            with patch.object(TxtConverter, "convert", failing_convert):
                results = converter.convert_directory(tmp_path)

            # One success, one failure
            successes = [r for r in results if r.success]
            failures = [r for r in results if not r.success]
            assert len(successes) == 1
            assert len(failures) == 1


class TestFormatFunctions:
    """Tests for formatting helper functions."""

    def test_format_scan_summary_empty(self):
        """Test formatting empty scan results."""
        result = format_scan_summary({})
        assert result == "No files found."

    def test_format_scan_summary_with_files(self):
        """Test formatting scan results with files."""
        groups = {".txt": [Path("a.txt"), Path("b.txt")], ".pdf": [Path("c.pdf")]}
        result = format_scan_summary(groups)

        assert "2 .txt" in result
        assert "1 .pdf" in result
        assert "3 total" in result

    def test_format_results_summary_all_success(self):
        """Test formatting results with all successes."""
        results = [
            ConversionResult(Path("a.txt"), Path("a.md"), True),
            ConversionResult(Path("b.txt"), Path("b.md"), True),
        ]
        summary = format_results_summary(results)

        assert "2 file(s) successfully" in summary
        assert "Failed" not in summary

    def test_format_results_summary_with_failures(self):
        """Test formatting results with failures."""
        results = [
            ConversionResult(Path("a.txt"), Path("a.md"), True),
            ConversionResult(Path("b.txt"), None, False, "Some error"),
        ]
        summary = format_results_summary(results)

        assert "1 file(s) successfully" in summary
        assert "Failed: 1" in summary
        assert "Some error" in summary


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful conversion result."""
        result = ConversionResult(
            source_path=Path("test.txt"),
            output_path=Path("test.md"),
            success=True,
        )
        assert result.success
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed conversion result."""
        result = ConversionResult(
            source_path=Path("test.txt"),
            output_path=None,
            success=False,
            error="Conversion failed",
        )
        assert not result.success
        assert result.error == "Conversion failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
