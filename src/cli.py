"""Unified cross-platform CLI entry point for Corpus Callosum."""

import click

from cli_dev import dev
from db.management import db
from orchestrations.cli import orchestrate
from tools.flashcards.cli import flashcards
from tools.quizzes.cli import quizzes
from tools.rag.cli import rag
from tools.summaries.cli import summaries
from tools.video.cli import video


@click.group()
@click.version_option(package_name="corpus-callosum")
def corpus() -> None:
    """Corpus Callosum — unified learning and knowledge management toolkit.

    Run any subcommand with --help for details.
    """


corpus.add_command(rag)
corpus.add_command(video)
corpus.add_command(orchestrate)
corpus.add_command(flashcards)
corpus.add_command(summaries)
corpus.add_command(quizzes)
corpus.add_command(db)
corpus.add_command(dev)


def main() -> None:
    """Entry point for the unified corpus CLI."""
    corpus()


if __name__ == "__main__":
    main()
