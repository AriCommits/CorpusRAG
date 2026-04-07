"""CLI interface for flashcards tool."""

import sys
from pathlib import Path

import click

from corpus_callosum.config.loader import load_config
from corpus_callosum.db.chroma import ChromaDBBackend

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
    # Load config
    config_data = load_config(config)
    cfg = FlashcardConfig.from_dict(config_data)
    
    # Initialize database and generator
    db = ChromaDBBackend(cfg.database)
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
