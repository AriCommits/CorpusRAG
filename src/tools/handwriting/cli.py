"""CLI interface for handwriting ingestion tool."""

from pathlib import Path

import click

from cli_common import load_cli_db

from .ingest_handwriting import ingest_handwriting
from .config import HandwritingConfig

# Import will happen inside function to support lazy loading but be patchable for tests
RAGAgent = None


@click.group()
def handwriting():
    """Handwritten document ingestion tools."""
    pass


@handwriting.command("ingest")
@click.argument("directory", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--collection",
    "-c",
    default="notes",
    show_default=True,
    help="Target ChromaDB collection name.",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    show_default=True,
    help="Recursively scan subdirectories.",
)
@click.option(
    "--vision-model",
    default="llava",
    show_default=True,
    help="Ollama vision model for OCR.",
)
@click.option(
    "--correction-model",
    default="mistral",
    show_default=True,
    help="Ollama text model for correction pass.",
)
@click.option(
    "--no-autocorrect",
    is_flag=True,
    default=False,
    help="Skip LLM correction pass (faster, less accurate).",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="Tags to apply to all ingested pages. Can be repeated.",
)
@click.option(
    "--context-window",
    default=1,
    show_default=True,
    type=int,
    help="Adjacent pages to include per chunk.",
)
@click.option(
    "--keep-preprocessed",
    is_flag=True,
    default=False,
    help="Keep preprocessed images after ingest (for debugging).",
)
@click.option(
    "--max-depth",
    default=None,
    type=int,
    help="Maximum directory depth to traverse. None = unlimited.",
)
@click.option(
    "--config",
    "-f",
    default="configs/base.yaml",
    help="Config file",
)
def ingest_cmd(
    directory,
    collection,
    recursive,
    vision_model,
    correction_model,
    no_autocorrect,
    tags,
    context_window,
    keep_preprocessed,
    max_depth,
    config,
):
    """
    Batch ingest a directory of handwritten document scans.

    Recursively walks DIRECTORY, OCRs each image, runs automatic
    correction, and stores searchable markdown in ChromaDB.

    Examples:

      corpus handwriting ingest ./journal_scans/ --collection journal

      corpus handwriting ingest ./notes/2024/ --collection notes --tags "#Year/2024"

      corpus handwriting ingest ./engineering/ --collection eng \\
          --vision-model llava:13b --correction-model mistral

      corpus handwriting ingest ./archive/ --collection archive --no-recursive
    """
    global RAGAgent
    if RAGAgent is None:
        from tools.rag.agent import RAGAgent as _RAGAgent
        RAGAgent = _RAGAgent

    cfg, db = load_cli_db(config, HandwritingConfig)
    agent = RAGAgent(cfg, db)

    click.echo(f"Scanning: {directory}")
    click.echo(f"Recursive: {recursive} | Collection: {collection}")
    click.echo(f"Vision model: {vision_model} | Correction model: {correction_model}")
    if tags:
        click.echo(f"Tags: {', '.join(tags)}")

    result = ingest_handwriting(
        root_dir=directory,
        collection=collection,
        agent=agent,
        recursive=recursive,
        vision_model=vision_model,
        correction_model=correction_model,
        autocorrect=not no_autocorrect,
        user_tags=list(tags) if tags else None,
        context_window=context_window,
        cleanup_preprocessed=not keep_preprocessed,
        max_depth=max_depth,
    )

    click.echo("\n✓ Ingest complete")
    click.echo(f"  Total images found:       {result.total_images_found}")
    click.echo(f"  Already ingested (skip):  {result.skipped_already_ingested}")
    click.echo(f"  Blank pages (skip):       {result.skipped_blank}")
    click.echo(f"  Pages ingested:           {result.pages_ingested}")
    if result.low_confidence_pages > 0:
        click.echo(
            f"  ⚠ Low confidence pages:  {result.low_confidence_pages} "
            f"(run `corpus handwriting review --collection {collection}` to inspect)"
        )
    if result.failed_pages > 0:
        click.echo(f"  ⚠ Failed pages:           {result.failed_pages}")
    if result.warnings_file:
        click.echo(f"  Warnings file:            {result.warnings_file}")


def main():
    """Entry point for corpus-handwriting CLI."""
    handwriting()


if __name__ == "__main__":
    main()
