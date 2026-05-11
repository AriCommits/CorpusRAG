"""Tools CLI group."""

import click

from cli_lazy import LazyGroup


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "rag": "tools.rag.cli:rag",
        "video": "tools.video.cli:video",
        "handwriting": "tools.handwriting.cli:handwriting",
        "summaries": "tools.summaries.cli:summaries",
        "learning": "tools.learning.cli:learning",
    },
)
def tools() -> None:
    """CorpusRAG tools — RAG, video, handwriting, summaries, and learning."""
