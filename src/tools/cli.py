"""Tools CLI group."""

import click

from cli_lazy import LazyGroup


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "rag": ("tools.rag.cli:rag", "RAG (Retrieval-Augmented Generation) tool."),
        "video": ("tools.video.cli:video", "Video transcription and processing tool."),
        "handwriting": (
            "tools.handwriting.cli:handwriting",
            "Handwritten document ingestion tools.",
        ),
        "summaries": ("tools.summaries.cli:summaries", "Generate summary from a collection."),
        "learning": ("tools.learning.cli:learning", "Learning tools — flashcards and quizzes."),
    },
)
def tools() -> None:
    """CorpusRAG tools — RAG, video, handwriting, summaries, and learning."""
