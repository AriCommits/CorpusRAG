"""CLI interface for flashcards tool."""

from pathlib import Path

import click

from cli_common import load_cli_db

from .config import FlashcardConfig
from .generator import FlashcardGenerator


@click.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--difficulty", "-d", default="intermediate", help="Difficulty level")
@click.option("--count", "-n", default=None, type=int, help="Number of flashcards")
def flashcards(collection: str, output: str, config: str, difficulty: str, count: int):
    """Generate flashcards from a collection."""
    cfg, db = load_cli_db(config, FlashcardConfig)
    generator = FlashcardGenerator(cfg, db)

    # Generate flashcards
    click.echo(f"Generating {count or cfg.cards_per_topic} flashcards from '{collection}'...")
    cards = generator.generate(collection, difficulty=difficulty, count=count)

    # Format output
    formatted = generator.format_flashcards(cards)

    # Write or print
    if output:
        Path(output).write_text(formatted)
        click.echo(f"✓ Wrote {len(cards)} flashcards to {output}")
    else:
        click.echo(formatted)


def main():
    """Entry point for corpus-flashcards CLI."""
    flashcards()


if __name__ == "__main__":
    main()
