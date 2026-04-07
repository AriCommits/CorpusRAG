"""CLI interface for RAG tool."""

import sys
from pathlib import Path

import click

from corpus_callosum.config.loader import load_config
from corpus_callosum.db.chroma import ChromaDBBackend

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
    # Load config
    config_data = load_config(config)
    cfg = RAGConfig.from_dict(config_data)
    
    # Initialize database and ingester
    db = ChromaDBBackend(cfg.database)
    ingester = RAGIngester(cfg, db)
    
    # Ingest documents
    click.echo(f"Ingesting documents from {path} into collection '{collection}'...")
    result = ingester.ingest_path(Path(path), collection)
    
    click.echo(f"✓ Indexed {result.files_indexed} files, {result.chunks_indexed} chunks")


@rag.command()
@click.argument("query")
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--top-k", "-k", default=None, type=int, help="Number of results")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def query(query: str, collection: str, top_k: int, config: str):
    """Query a RAG collection."""
    # Load config
    config_data = load_config(config)
    cfg = RAGConfig.from_dict(config_data)
    
    # Initialize database and agent
    db = ChromaDBBackend(cfg.database)
    agent = RAGAgent(cfg, db)
    
    # Execute query
    click.echo(f"Querying collection '{collection}'...\n")
    response, chunks = agent.query(query, collection, top_k=top_k)
    
    # Display results
    click.echo("Response:")
    click.echo(response)
    click.echo(f"\n(Retrieved {len(chunks)} chunks)")


@rag.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def chat(collection: str, config: str):
    """Interactive chat with RAG agent."""
    # Load config
    config_data = load_config(config)
    cfg = RAGConfig.from_dict(config_data)
    
    # Initialize database and agent
    db = ChromaDBBackend(cfg.database)
    agent = RAGAgent(cfg, db)
    
    click.echo(f"RAG Chat - Collection: {collection}")
    click.echo("Type 'exit' or 'quit' to end the session\n")
    
    while True:
        try:
            message = click.prompt("You", type=str)
            if message.lower() in ["exit", "quit"]:
                break
            
            response = agent.chat(message, collection)
            click.echo(f"Agent: {response}\n")
        except (KeyboardInterrupt, EOFError):
            break
    
    click.echo("\nGoodbye!")


def main():
    """Entry point for corpus-rag CLI."""
    rag()


if __name__ == "__main__":
    main()
