"""CLI interface for summaries tool."""

import sys
from pathlib import Path

import click

from corpus_callosum.config.loader import load_config
from corpus_callosum.db.chroma import ChromaDBBackend

from .config import SummaryConfig
from .generator import SummaryGenerator


@click.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--length", "-l", default="medium", type=click.Choice(["short", "medium", "long"]), help="Summary length")
def summaries(collection: str, output: str, config: str, length: str):
    """Generate summary from a collection."""
    # Load config
    config_data = load_config(config)
    cfg = SummaryConfig.from_dict(config_data)
    cfg.summary_length = length
    
    # Initialize database and generator
    db = ChromaDBBackend(cfg.database)
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
