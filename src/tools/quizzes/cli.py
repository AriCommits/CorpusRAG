"""CLI interface for quizzes tool."""

import sys
from pathlib import Path

import click


def __getattr__(name: str):
    """Lazily provide heavy symbols on attribute access (keeps import cheap)."""
    if name == "load_cli_db":
        from cli_common import load_cli_db

        return load_cli_db
    if name == "QuizConfig":
        from .config import QuizConfig

        return QuizConfig
    if name == "QuizGenerator":
        from .generator import QuizGenerator

        return QuizGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _resolve(name: str):
    """Resolve a (possibly patched) module-level symbol at call time."""
    return getattr(sys.modules[__name__], name)


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
    load_cli_db = _resolve("load_cli_db")
    QuizConfig = _resolve("QuizConfig")
    QuizGenerator = _resolve("QuizGenerator")
    cfg, db = load_cli_db(config, QuizConfig)
    cfg.format = format

    generator = QuizGenerator(cfg, db)

    # Generate quiz
    click.echo(
        f"Generating {count or cfg.questions_per_topic} quiz questions from '{collection}'..."
    )
    questions = generator.generate(collection, count=count)

    if format in ["json", "csv"]:
        if not output:
            output = f"quiz_{collection}.{format}"
        from .export import QuizExporter

        exporter = QuizExporter()
        # Convert questions to list of dicts for export
        quiz_data = [q.to_dict() if hasattr(q, "to_dict") else q for q in questions]
        if format == "json":
            exporter.export_json(quiz_data, output)
        else:
            exporter.export_csv(quiz_data, output)
        click.echo(f"✓ Exported quiz to {format.upper()}: {output}")
        return

    # Format output (markdown)
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
