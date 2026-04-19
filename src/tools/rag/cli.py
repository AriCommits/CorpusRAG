"""CLI interface for RAG tool."""

import sys
from pathlib import Path

import click

from cli_common import load_cli_db

from .agent import RAGAgent
from .config import RAGConfig
from .ingest import RAGIngester
from .tui import RAGApp


def _validate_filter_value(value: str, field_name: str) -> str:
    """Validate a metadata filter value for safe ChromaDB usage.

    Args:
        value: The filter value to validate
        field_name: Name of the field being filtered (for error messages)

    Returns:
        The validated value

    Raises:
        ValueError: If the value is invalid
    """
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")

    if len(value) > 256:
        raise ValueError(f"{field_name} is too long (max 256 characters)")

    # Reject values containing operators or special ChromaDB syntax
    if any(char in value for char in ["$", "{", "}", "[", "]", "|"]):
        raise ValueError(
            f"{field_name} contains invalid characters. "
            "Only alphanumeric characters, spaces, hyphens, and underscores allowed"
        )

    return value


@click.group()
def rag():
    """RAG (Retrieval-Augmented Generation) tool."""
    pass


@rag.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def ingest(path: str, collection: str, config: str):
    """Ingest documents into a RAG collection."""
    cfg, db = load_cli_db(config, RAGConfig)
    ingester = RAGIngester(cfg, db)

    click.echo(f"Ingesting documents from {path} into collection '{collection}'...")
    result = ingester.ingest_path(Path(path), collection)
    click.echo(f"Indexed {result.files_indexed} files, {result.chunks_indexed} chunks")


@rag.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--dry-run", is_flag=True, help="Report changes without applying them")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def sync(path: str, collection: str, dry_run: bool, config: str):
    """Sync a directory with a RAG collection (detect new, modified, deleted files)."""
    cfg, db = load_cli_db(config, RAGConfig)
    from .sync import RAGSyncer

    syncer = RAGSyncer(cfg, db)

    click.echo(f"Syncing '{path}' -> collection '{collection}'...")
    res = syncer.sync(path, collection, dry_run=dry_run)

    click.echo(f"\n  NEW:       {len(res.new_files)} files")
    click.echo(f"  MODIFIED:  {len(res.modified_files)} files")
    click.echo(f"  DELETED:   {len(res.deleted_files)} files")
    click.echo(f"  UNCHANGED: {len(res.unchanged_files)} files\n")

    if dry_run:
        click.echo("[DRY RUN] Sync complete: +0 chunks, -0 chunks")
    else:
        click.echo(f"Sync complete: +{res.chunks_added} chunks, -{res.chunks_removed} chunks")


@rag.command()
@click.argument("query")
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--top-k", "-k", default=None, type=int, help="Number of results")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (can be used multiple times)")
@click.option(
    "--section",
    "-s",
    multiple=True,
    help="Filter by section header (can be used multiple times)",
)
@click.option(
    "--strategy",
    type=click.Choice(["hybrid", "semantic", "keyword"]),
    default=None,
    help="Retrieval strategy override",
)
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def query(
    query: str,
    collection: str,
    top_k: int,
    tag: tuple[str, ...],
    section: tuple[str, ...],
    strategy: str | None,
    config: str,
):
    """Query a RAG collection with optional metadata filtering."""
    cfg, db = load_cli_db(config, RAGConfig)

    # Override strategy if provided
    if strategy:
        cfg.strategy = strategy

    agent = RAGAgent(cfg, db)

    # Build where filter for metadata
    where = None
    if tag or section:
        tag_filter = None
        if tag:
            # Validate all tag values for safe ChromaDB usage
            try:
                validated_tags = [_validate_filter_value(t, f"tag '{t}'") for t in tag]
            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                return

            if len(validated_tags) == 1:
                tag_filter = {"tags": {"$contains": validated_tags[0]}}
            else:
                tag_filter = {"$or": [{"tags": {"$contains": t}} for t in validated_tags]}

        section_filter = None
        if section:
            # Validate all section values for safe ChromaDB usage
            try:
                validated_sections = [_validate_filter_value(s, f"section '{s}'") for s in section]
            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                return

            # Filter for documents with specific section headers
            # Only use keys that actually exist in the metadata
            section_filter = {
                "$or": [
                    {"Document Title": {"$in": validated_sections}},
                    {"Subsection": {"$in": validated_sections}},
                ]
            }

        if tag_filter and section_filter:
            where = {"$and": [tag_filter, section_filter]}
        elif tag_filter:
            where = tag_filter
        else:
            where = section_filter

    click.echo(f"Querying collection '{collection}'...\n")
    response = agent.query(query, collection, top_k=top_k, where=where)
    docs = agent.retrieve(query, collection, top_k=top_k, where=where)

    click.echo("Response:")
    click.echo(response)
    click.echo(f"\n(Retrieved {len(docs)} documents)")


@rag.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (can be used multiple times)")
@click.option(
    "--section",
    "-s",
    multiple=True,
    help="Filter by section header (can be used multiple times)",
)
@click.option(
    "--strategy",
    type=click.Choice(["hybrid", "semantic", "keyword"]),
    default=None,
    help="Retrieval strategy override",
)
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def chat(
    collection: str,
    tag: tuple[str, ...],
    section: tuple[str, ...],
    strategy: str | None,
    config: str,
):
    """Interactive chat with RAG agent with optional metadata filtering."""
    cfg, db = load_cli_db(config, RAGConfig)

    # Override strategy if provided
    if strategy:
        cfg.strategy = strategy

    agent = RAGAgent(cfg, db)

    # Build where filter for metadata
    where = None
    if tag or section:
        tag_filter = None
        if tag:
            if len(tag) == 1:
                tag_filter = {"tags": {"$contains": tag[0]}}
            else:
                tag_filter = {"$or": [{"tags": {"$contains": t}} for t in tag]}

        section_filter = None
        if section:
            # Only use keys that actually exist in the metadata
            section_filter = {
                "$or": [
                    {"Document Title": {"$in": list(section)}},
                    {"Subsection": {"$in": list(section)}},
                ]
            }

        if tag_filter and section_filter:
            where = {"$and": [tag_filter, section_filter]}
        elif tag_filter:
            where = tag_filter
        else:
            where = section_filter

    click.echo(f"RAG Chat - Collection: {collection}")
    if where:
        click.echo(f"Filters: tags={tag}, sections={section}")
    click.echo("Type 'exit' or 'quit' to end the session\n")

    while True:
        try:
            message = click.prompt("You", type=str)
            if message.lower() in ["exit", "quit"]:
                break

            response = agent.chat(message, collection, where=where)
            click.echo(f"Agent: {response}\n")
        except (KeyboardInterrupt, EOFError):
            break

    click.echo("\nGoodbye!")


@rag.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def ui(collection: str, config: str):
    """Launch the Terminal User Interface."""
    # Check if setup has been completed
    marker_file = Path(".corpus_setup_complete")
    if not marker_file.exists():
        click.echo("Welcome to CorpusRAG!")
        click.echo(
            "It looks like this is your first time running the TUI.\n"
            "Let's set up your configuration...\n"
        )

        # Run setup wizard
        from setup_wizard import run_setup_wizard

        exit_code = run_setup_wizard()
        if exit_code != 0:
            click.echo("Setup failed. Please run 'corpus setup' to try again.")
            sys.exit(1)

        click.echo("\nSetup complete! Launching TUI...\n")

    # Launch the TUI
    cfg, db = load_cli_db(config, RAGConfig)
    agent = RAGAgent(cfg, db)
    app = RAGApp(agent, collection)
    app.run()


def main():
    """Entry point for corpus-rag CLI."""
    rag()


if __name__ == "__main__":
    main()
