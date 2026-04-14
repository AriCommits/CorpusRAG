"""CLI interface for quizzes tool."""

from pathlib import Path

import click

from cli_common import load_cli_db

from .config import QuizConfig
from .generator import QuizGenerator


@click.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--count", "-n", default=None, type=int, help="Number of questions")
@click.option(
    "--format",
    "-fmt",
    default="markdown",
    type=click.Choice(["markdown", "json", "csv"]),
    help="Output format",
)
def quizzes(collection: str, output: str, config: str, count: int, format: str):
    """Generate quiz questions from a collection."""
    cfg, db = load_cli_db(config, QuizConfig)
    cfg.format = format

    generator = QuizGenerator(cfg, db)

    # Generate quiz
    click.echo(
        f"Generating {count or cfg.questions_per_topic} quiz questions from '{collection}'..."
    )
    questions = generator.generate(collection, count=count)

    # Format output
    formatted = generator.format_quiz(questions)

    # Write or print
    if output:
        Path(output).write_text(formatted)
        click.echo(f"✓ Wrote {len(questions)} questions to {output}")
    else:
        click.echo(formatted)


def main():
    """Entry point for corpus-quizzes CLI."""
    quizzes()


if __name__ == "__main__":
    main()
