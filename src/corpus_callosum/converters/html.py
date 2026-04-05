"""HTML to Markdown converter."""

from __future__ import annotations

from pathlib import Path

from .base import BaseConverter


class HtmlConverter(BaseConverter):
    """Convert HTML files to Markdown."""

    extensions = (".html", ".htm")

    def convert(self, source: Path) -> str:
        """
        Convert HTML file to markdown.

        Removes script/style tags and converts HTML elements to markdown syntax.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise RuntimeError(
                "HTML conversion requires beautifulsoup4. Install with: pip install beautifulsoup4"
            ) from exc

        try:
            from markdownify import markdownify
        except ImportError as exc:
            raise RuntimeError(
                "HTML conversion requires markdownify. Install with: pip install markdownify"
            ) from exc

        html = source.read_text(encoding="utf-8", errors="ignore")

        # Parse and clean HTML
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Remove comments
        from bs4 import Comment

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Convert to markdown
        markdown = markdownify(str(soup), heading_style="ATX", strip=["a"])

        # Clean up excessive whitespace
        lines = []
        prev_empty = False
        for raw_line in markdown.split("\n"):
            line = raw_line.rstrip()
            is_empty = not line
            if is_empty and prev_empty:
                continue
            lines.append(line)
            prev_empty = is_empty

        return "\n".join(lines).strip()
