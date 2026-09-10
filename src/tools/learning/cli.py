"""Learning tools CLI group."""

import click

from cli_lazy import LazyGroup


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "flashcards": (
            "tools.flashcards.cli:flashcards",
            "Generate flashcards from a collection.",
        ),
        "quizzes": ("tools.quizzes.cli:quizzes", "Generate quiz questions from a collection."),
    },
)
def learning() -> None:
    """Learning tools — flashcards and quizzes."""
