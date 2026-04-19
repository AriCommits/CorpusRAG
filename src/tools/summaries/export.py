from datetime import datetime
from pathlib import Path


class MarkdownSummaryExporter:
    """Export summaries to Markdown format with YAML frontmatter."""

    def export(self, summary_text: str, collection: str, topic: str, output_path: Path | str):
        """Export summary to markdown file."""
        frontmatter = f"""---
collection: {collection}
topic: "{topic}"
date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
tool: CorpusRAG Summary
---

"""
        content = frontmatter + summary_text
        Path(output_path).write_text(content, encoding="utf-8")
