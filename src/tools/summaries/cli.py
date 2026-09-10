"""CLI interface for summaries tool."""

import sys
from pathlib import Path

import click


def __getattr__(name: str):
    """Lazily provide heavy symbols on attribute access (keeps import cheap)."""
    if name == "load_cli_db":
        from cli_common import load_cli_db

        return load_cli_db
    if name == "SummaryConfig":
        from .config import SummaryConfig

        return SummaryConfig
    if name == "SummaryGenerator":
        from .generator import SummaryGenerator

        return SummaryGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _resolve(name: str):
    """Resolve a (possibly patched) module-level symbol at call time."""
    return getattr(sys.modules[__name__], name)


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
    load_cli_db = _resolve("load_cli_db")
    SummaryConfig = _resolve("SummaryConfig")
    SummaryGenerator = _resolve("SummaryGenerator")
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
        exporter.export(summary["summary"], collection, f"Summary of {collection}", output)
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
