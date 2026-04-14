"""CLI interface for summaries tool."""

from pathlib import Path

import click

from cli_common import load_cli_db

from .config import SummaryConfig
from .generator import SummaryGenerator


@click.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option(
    "--length",
    "-l",
    default="medium",
    type=click.Choice(["short", "medium", "long"]),
    help="Summary length",
)
def summaries(collection: str, output: str, config: str, length: str):
    """Generate summary from a collection."""
    cfg, db = load_cli_db(config, SummaryConfig)
    cfg.summary_length = length

    generator = SummaryGenerator(cfg, db)

    # Generate summary
    click.echo(f"Generating {length} summary from '{collection}'...")
    summary = generator.generate(collection)

    # Format output
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
