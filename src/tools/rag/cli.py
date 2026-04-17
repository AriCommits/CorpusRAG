"""CLI interface for RAG tool."""

from pathlib import Path

import click

from cli_common import load_cli_db

from .agent import RAGAgent
from .config import RAGConfig
from .ingest import RAGIngester


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
@click.argument("query")
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--top-k", "-k", default=None, type=int, help="Number of results")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (can be used multiple times)")
@click.option("--section", "-s", multiple=True, help="Filter by section header (can be used multiple times)")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def query(query: str, collection: str, top_k: int, tag: tuple[str, ...], section: tuple[str, ...], config: str):
    """Query a RAG collection with optional metadata filtering."""
    cfg, db = load_cli_db(config, RAGConfig)
    agent = RAGAgent(cfg, db)

    # Build where filter for metadata
    where = None
    if tag or section:
        where = {}
        if tag:
            # Filter for documents that have any of the specified tags
            where["tags"] = {"$in": list(tag)}
        if section:
            # Filter for documents with specific section headers
            # This filters on Document Title, Primary Section, or Subsection metadata
            section_filter = {"$or": [
                {"Document Title": {"$in": list(section)}},
                {"Primary Section": {"$in": list(section)}},
                {"Subsection": {"$in": list(section)}},
            ]}
            if "tags" in where:
                # Combine tag and section filters
                where = {"$and": [where, section_filter]}
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
@click.option("--section", "-s", multiple=True, help="Filter by section header (can be used multiple times)")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def chat(collection: str, tag: tuple[str, ...], section: tuple[str, ...], config: str):
    """Interactive chat with RAG agent with optional metadata filtering."""
    cfg, db = load_cli_db(config, RAGConfig)
    agent = RAGAgent(cfg, db)

    # Build where filter for metadata
    where = None
    if tag or section:
        where = {}
        if tag:
            where["tags"] = {"$in": list(tag)}
        if section:
            section_filter = {"$or": [
                {"Document Title": {"$in": list(section)}},
                {"Primary Section": {"$in": list(section)}},
                {"Subsection": {"$in": list(section)}},
            ]}
            if "tags" in where:
                where = {"$and": [where, section_filter]}
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


def main():
    """Entry point for corpus-rag CLI."""
    rag()


if __name__ == "__main__":
    main()
