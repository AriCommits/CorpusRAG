"""CLI interface for summaries tool."""

from pathlib import Path

import click

from cli_common import load_cli_db

from .config import SummaryConfig
from .generator import SummaryGenerator


@click.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--output", "-o", default=None, help="Output file")
@click.option(
    "--export",
    "-e",
    type=click.Choice(["markdown", "text"]),
    default="markdown",
    help="Export format",
)
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option(
    "--length",
    "-l",
    default="medium",
    type=click.Choice(["short", "medium", "long"]),
    help="Summary length",
)
def summaries(collection: str, output: str, export: str, config: str, length: str):
    """Generate summary from a collection."""
    cfg, db = load_cli_db(config, SummaryConfig)
    cfg.summary_length = length

    generator = SummaryGenerator(cfg, db)

    # Generate summary
    click.echo(f"Generating {length} summary from '{collection}'...")
    summary = generator.generate(collection)

    if export == "markdown":
        if not output:
            output = f"summary_{collection}.md"
        from .export import MarkdownSummaryExporter

        exporter = MarkdownSummaryExporter()
        exporter.export(summary.text, collection, f"Summary of {collection}", output)
        click.echo(f"✓ Exported summary to Markdown: {output}")
        return

    # Format output (plain text)
    formatted = generator.format_summary(summary)

    # Write or print
    if output:
        Path(output).write_text(formatted)
        click.echo(f"✓ Wrote summary to {output}")
    else:
        click.echo(formatted)


def main():
    """Entry point for corpus-summaries CLI."""
    summaries()


if __name__ == "__main__":
    main()
