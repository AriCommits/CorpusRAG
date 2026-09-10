"""CLI interface for handwriting ingestion tool."""

import sys
from pathlib import Path

import click


def __getattr__(name: str):
    """Lazily provide heavy symbols on attribute access.

    Keeps module import cheap while allowing existing tests to patch
    ``tools.handwriting.cli.load_cli_db`` / ``ingest_handwriting`` /
    ``RAGAgent`` and normal attribute access to resolve the real
    implementation on demand.
    """
    if name == "load_cli_db":
        from cli_common import load_cli_db

        return load_cli_db
    if name == "HandwritingConfig":
        from .config import HandwritingConfig

        return HandwritingConfig
    if name == "ingest_handwriting":
        from .ingest_handwriting import ingest_handwriting

        return ingest_handwriting
    if name == "RAGAgent":
        from tools.rag.agent import RAGAgent

        return RAGAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _resolve(name: str):
    """Resolve a (possibly patched) module-level symbol at call time."""
    return getattr(sys.modules[__name__], name)


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
    load_cli_db = _resolve("load_cli_db")
    HandwritingConfig = _resolve("HandwritingConfig")
    ingest_handwriting = _resolve("ingest_handwriting")
    RAGAgent = _resolve("RAGAgent")

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
        extra = f" (see {result.warnings_file})" if result.warnings_file else ""
        click.echo(f"  ⚠ Low confidence pages:  {result.low_confidence_pages}{extra}")
    if result.failed_pages > 0:
        click.echo(f"  ⚠ Failed pages:           {result.failed_pages}")
    if result.warnings_file:
        click.echo(f"  Warnings file:            {result.warnings_file}")


def main():
    """Entry point for corpus-handwriting CLI."""
    handwriting()


if __name__ == "__main__":
    main()
