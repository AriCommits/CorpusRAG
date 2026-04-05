"""File conversion utility for CorpusCallosum.

Converts various document formats to Markdown for RAG ingestion.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

from .converters import ConversionResult, get_all_converters
from .converters.base import BaseConverter

logger = logging.getLogger(__name__)

# Default output directory name
DEFAULT_OUTPUT_DIR = "corpus_converted"


class FileConverter:
    """Orchestrates file conversion for a directory."""

    def __init__(self) -> None:
        self._converters: dict[str, BaseConverter] = {}
        self._register_all()

    def _register_all(self) -> None:
        """Register all available converters."""
        for converter in get_all_converters():
            for ext in converter.extensions:
                self._converters[ext.lower()] = converter

    def get_supported_extensions(self) -> set[str]:
        """Return all extensions that can be converted."""
        return set(self._converters.keys())

    def get_converter(self, extension: str) -> BaseConverter | None:
        """Get converter for a file extension."""
        return self._converters.get(extension.lower())

    def scan_directory(self, path: Path) -> dict[str, list[Path]]:
        """
        Scan directory and group files by extension.

        Args:
            path: Directory to scan

        Returns:
            Dictionary mapping extensions to lists of file paths
        """
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        groups: dict[str, list[Path]] = defaultdict(list)

        for file_path in path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext:
                    groups[ext].append(file_path)

        # Sort files within each group
        for _ext, files in groups.items():
            files.sort()

        return dict(groups)

    def get_convertible_files(self, path: Path) -> dict[str, list[Path]]:
        """Get only files that can be converted."""
        all_files = self.scan_directory(path)
        supported = self.get_supported_extensions()
        return {ext: files for ext, files in all_files.items() if ext in supported}

    def get_unconvertible_files(self, path: Path) -> dict[str, list[Path]]:
        """Get files that cannot be converted (unsupported formats)."""
        all_files = self.scan_directory(path)
        supported = self.get_supported_extensions()
        # Also exclude already-converted markdown files
        excluded = supported | {".md"}
        return {ext: files for ext, files in all_files.items() if ext not in excluded}

    def flatten_filename(self, source_dir: Path, file_path: Path) -> str:
        """
        Convert nested path to flat filename.

        Example: source_dir/sub/dir/file.pdf → sub_dir_file.md
        """
        try:
            relative = file_path.relative_to(source_dir)
        except ValueError:
            relative = Path(file_path.name)

        # Replace path separators with underscores
        parts = list(relative.parts)
        if parts:
            # Change extension to .md
            stem = Path(parts[-1]).stem
            parts[-1] = stem

        flat_name = "_".join(parts) + ".md"
        return flat_name

    def convert_file(
        self,
        source: Path,
        output_path: Path,
    ) -> ConversionResult:
        """
        Convert a single file to markdown.

        Args:
            source: Source file path
            output_path: Output file path

        Returns:
            ConversionResult with success/failure info
        """
        ext = source.suffix.lower()
        converter = self.get_converter(ext)

        if converter is None:
            return ConversionResult(
                source_path=source,
                output_path=None,
                success=False,
                error=f"No converter for extension: {ext}",
            )

        try:
            markdown = converter.convert(source)
            output_path.write_text(markdown, encoding="utf-8")
            return ConversionResult(
                source_path=source,
                output_path=output_path,
                success=True,
            )
        except Exception as e:
            logger.warning("Failed to convert %s: %s", source, e)
            return ConversionResult(
                source_path=source,
                output_path=None,
                success=False,
                error=str(e),
            )

    def convert_directory(
        self,
        source_dir: Path,
        output_subdir: str = DEFAULT_OUTPUT_DIR,
    ) -> list[ConversionResult]:
        """
        Convert all supported files in a directory to markdown.

        Args:
            source_dir: Directory containing source files
            output_subdir: Name of subdirectory for converted files

        Returns:
            List of ConversionResult objects
        """
        source_dir = Path(source_dir).resolve()
        output_dir = source_dir / output_subdir

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get convertible files
        file_groups = self.get_convertible_files(source_dir)

        results: list[ConversionResult] = []
        used_names: set[str] = set()

        for _ext, files in file_groups.items():
            for file_path in files:
                # Skip files already in the output directory
                try:
                    file_path.relative_to(output_dir)
                    continue  # Skip files in output dir
                except ValueError:
                    pass  # File is not in output dir, continue

                # Generate unique output filename
                base_name = self.flatten_filename(source_dir, file_path)
                output_name = base_name
                counter = 1

                while output_name in used_names:
                    stem = Path(base_name).stem
                    output_name = f"{stem}_{counter}.md"
                    counter += 1

                used_names.add(output_name)
                output_path = output_dir / output_name

                # Convert the file
                result = self.convert_file(file_path, output_path)
                results.append(result)

        return results


def format_scan_summary(file_groups: dict[str, list[Path]]) -> str:
    """Format a summary of scanned files."""
    if not file_groups:
        return "No files found."

    parts = []
    total = 0
    for ext, files in sorted(file_groups.items()):
        count = len(files)
        total += count
        parts.append(f"{count} {ext}")

    return f"Found: {', '.join(parts)} ({total} total)"


def format_results_summary(results: list[ConversionResult]) -> str:
    """Format a summary of conversion results."""
    success = sum(1 for r in results if r.success)
    failed = len(results) - success

    lines = [f"\nConverted {success} file(s) successfully."]
    if failed:
        lines.append(f"Failed: {failed} file(s)")
        for r in results:
            if not r.success:
                lines.append(f"  - {r.source_path.name}: {r.error}")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point for corpus-convert."""
    parser = argparse.ArgumentParser(
        prog="corpus-convert",
        description="Convert documents to Markdown for RAG ingestion",
    )
    parser.add_argument(
        "path",
        help="Directory containing files to convert",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Name of output subdirectory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be converted without actually converting",
    )

    args = parser.parse_args()
    source_path = Path(args.path).expanduser().resolve()

    if not source_path.exists():
        print(f"Error: Path does not exist: {source_path}", file=sys.stderr)
        sys.exit(1)

    if not source_path.is_dir():
        print(f"Error: Path is not a directory: {source_path}", file=sys.stderr)
        sys.exit(1)

    converter = FileConverter()

    print(f"Scanning {source_path}...")
    convertible = converter.get_convertible_files(source_path)
    unconvertible = converter.get_unconvertible_files(source_path)

    print(format_scan_summary(convertible))

    if unconvertible:
        skipped_count = sum(len(files) for files in unconvertible.values())
        exts = ", ".join(sorted(unconvertible.keys()))
        print(f"Skipping {skipped_count} file(s) with unsupported extensions: {exts}")

    if not convertible:
        print("No files to convert.")
        sys.exit(0)

    if args.dry_run:
        print("\n[Dry run] Would convert:")
        for _ext, files in sorted(convertible.items()):
            for f in files:
                flat_name = converter.flatten_filename(source_path, f)
                print(f"  {f.name} → {args.output_dir}/{flat_name}")
        sys.exit(0)

    print(f"\nConverting to {args.output_dir}/...")
    results = converter.convert_directory(source_path, args.output_dir)

    # Print individual results
    for result in results:
        if result.success:
            # output_path is guaranteed non-None when success is True
            assert result.output_path is not None
            print(f"  ✓ {result.source_path.name} → {result.output_path.name}")
        else:
            print(f"  ✗ {result.source_path.name}: {result.error}")

    print(format_results_summary(results))

    # Exit with error if any conversions failed
    if any(not r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
