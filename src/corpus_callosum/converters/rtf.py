"""RTF to Markdown converter."""

from __future__ import annotations

from pathlib import Path

from .base import BaseConverter


class RtfConverter(BaseConverter):
    """Convert RTF (Rich Text Format) files to Markdown."""

    extensions = (".rtf",)

    def convert(self, source: Path) -> str:
        """
        Convert RTF file to markdown.

        Strips RTF formatting and extracts plain text.
        """
        try:
            from striprtf.striprtf import rtf_to_text
        except ImportError as exc:
            raise RuntimeError(
                "RTF conversion requires striprtf. Install with: pip install striprtf"
            ) from exc

        rtf_content = source.read_text(encoding="utf-8", errors="ignore")
        text: str = rtf_to_text(rtf_content)

        return text.strip()
