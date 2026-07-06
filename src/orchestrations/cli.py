"""CLI for orchestrations."""

from pathlib import Path

import click

from cli_common import load_cli_db


@click.group()
def orchestrate():
    """Orchestration workflows for CorpusRAG."""
    pass


@orchestrate.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--course", "-c", required=True, help="Course identifier (e.g., BIOL101)")
@click.option("--lecture", "-l", required=True, type=int, help="Lecture number")
@click.option("--skip-clean", is_flag=True, help="Skip transcript cleaning")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-cfg", default="configs/base.yaml", help="Config file")
def lecture_pipeline(
    video_path: str,
    course: str,
    lecture: int,
    skip_clean: bool,
    output: str,
    config: str,
):
    """Process a lecture video into complete study materials."""
    from orchestrations import LecturePipelineOrchestrator

    config_data, db = load_cli_db(config)
    orchestrator = LecturePipelineOrchestrator(config_data, db)

    click.echo(f"Processing lecture {lecture} for course {course}...")
    result = orchestrator.process_lecture(
        video_path=Path(video_path),
        course=course,
        lecture_num=lecture,
        skip_clean=skip_clean,
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
