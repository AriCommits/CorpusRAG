"""Learning tools CLI group."""

import click

from cli_lazy import LazyGroup


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "flashcards": "tools.flashcards.cli:flashcards",
        "quizzes": "tools.quizzes.cli:quizzes",
    },
)
def learning() -> None:
    """Learning tools — flashcards and quizzes."""
