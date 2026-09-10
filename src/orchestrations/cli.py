"""CLI for orchestrations."""

import sys
from pathlib import Path

import click


def __getattr__(name: str):
    """Lazily provide ``load_cli_db`` on attribute access.

    Keeps module import cheap while allowing existing tests to patch
    ``orchestrations.cli.load_cli_db``.
    """
    if name == "load_cli_db":
        from cli_common import load_cli_db

        return load_cli_db
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _resolve(name: str):
    """Resolve a (possibly patched) module-level symbol at call time."""
    return getattr(sys.modules[__name__], name)


@click.group()
def orchestrate():
    """Orchestration workflows for CorpusRAG."""
    pass


@orchestrate.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--course", "-c", required=True, help="Course identifier (e.g., BIOL101)")
@click.option("--lecture", "-l", required=True, type=int, help="Lecture number")
@click.option(
    "--skip-clean/--no-skip-clean",
    default=None,
    help="Skip transcript cleaning (overrides config when set)",
)
@click.option(
    "--flashcard-count",
    type=int,
    default=None,
    help="Number of flashcards to generate (overrides config when set)",
)
@click.option(
    "--quiz-count",
    type=int,
    default=None,
    help="Number of quiz questions to generate (overrides config when set)",
)
@click.option(
    "--summary-length",
    type=click.Choice(["short", "medium", "long"]),
    default=None,
    help="Summary length (overrides config when set)",
)
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-cfg", default="configs/base.yaml", help="Config file")
def lecture_pipeline(
    video_path: str,
    course: str,
    lecture: int,
    skip_clean: bool | None,
    flashcard_count: int | None,
    quiz_count: int | None,
    summary_length: str | None,
    output: str | None,
    config: str,
):
    """Process a lecture video into complete study materials.

    Only the video path, ``--course`` and ``--lecture`` are required. Every
    other option falls back to the configured value when omitted; supplying a
    flag overrides the configured value for this run.
    """
    from orchestrations import LecturePipelineOrchestrator

    load_cli_db = _resolve("load_cli_db")
    config_data, db = load_cli_db(config)
    orchestrator = LecturePipelineOrchestrator(config_data, db)

    click.echo(f"Processing lecture {lecture} for course {course}...")
    result = orchestrator.process_lecture(
        video_path=Path(video_path),
        course=course,
        lecture_num=lecture,
        skip_clean=skip_clean,
        flashcard_count=flashcard_count,
        quiz_count=quiz_count,
        summary_length=summary_length,
    )

    formatted = orchestrator.format_lecture_materials(result)

    if output:
        Path(output).write_text(formatted)
        click.echo(f"✓ Lecture materials written to {output}")
    else:
        click.echo("\n" + formatted)


def main():
    """Entry point for orchestrations CLI."""
    orchestrate()


if __name__ == "__main__":
    main()
