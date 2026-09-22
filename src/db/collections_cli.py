"""CLI commands for managing ChromaDB collections."""

import sys

import click


def __getattr__(name: str):
    """Lazily provide heavy symbols on attribute access.

    Keeps module import cheap (``click`` only) so ``corpus collections --help``
    does not import ``rich`` / ``chromadb`` / ``config``. Existing tests that
    patch ``db.collections_cli.load_cli_db`` still work because the attribute
    is resolvable on access.
    """
    if name == "load_cli_db":
        from cli_common import load_cli_db

        return load_cli_db
    if name == "BaseConfig":
        from config import BaseConfig

        return BaseConfig
    if name == "ChromaDBBackend":
        from db.chroma import ChromaDBBackend

        return ChromaDBBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _resolve(name: str):
    """Resolve a (possibly patched) module-level symbol at call time."""
    return getattr(sys.modules[__name__], name)


def _console():
    """Create a rich console lazily (imports ``rich`` on demand)."""
    from rich.console import Console

    return Console()


@click.group(name="collections")
def collections_cmd() -> None:
    """Manage vector database collections."""


@collections_cmd.command(name="list")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def list_collections(config: str) -> None:
    """List all available collections."""
    from rich.table import Table

    load_cli_db = _resolve("load_cli_db")
    BaseConfig = _resolve("BaseConfig")
    console = _console()
    cfg, db = load_cli_db(config, BaseConfig)

    cols = db.list_collections()
    if not cols:
        console.print("No collections found.")
        return

    table = Table(title="Collections")
    table.add_column("Name", style="cyan")
    table.add_column("Document Count", justify="right", style="magenta")
    table.add_column("Estimated Size", justify="right", style="green")

    for c in cols:
        stats = db.get_collection_stats(c)
        table.add_row(
            c,
            str(stats.get("doc_count", "N/A")),
            str(stats.get("size_estimate", "N/A")) + " bytes",
        )

    console.print(table)


@collections_cmd.command(name="info")
@click.argument("name")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def info_collection(name: str, config: str) -> None:
    """Show detailed stats for a collection."""
    from rich.table import Table

    load_cli_db = _resolve("load_cli_db")
    BaseConfig = _resolve("BaseConfig")
    ChromaDBBackend = _resolve("ChromaDBBackend")
    console = _console()
    cfg, db = load_cli_db(config, BaseConfig)

    if not isinstance(db, ChromaDBBackend):
        console.print("[red]Stats are only supported on ChromaDB backends.[/red]")
        return

    # Check collection exists
    collections = db.list_collections()
    if name not in collections:
        console.print(f"[red]Error:[/red] Collection '{name}' not found.")
        console.print(
            f"Available collections: {', '.join(collections) if collections else '(none)'}"
        )
        return

    try:
        stats = db.get_collection_stats(name)

        table = Table(title=f"Stats for: {name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Document Count", str(stats.get("doc_count", "N/A")))
        table.add_row("Chunk Count", str(stats.get("chunk_count", "N/A")))
        table.add_row("Unique Files", str(stats.get("unique_files", "N/A")))
        table.add_row("Estimated Size (bytes)", str(stats.get("size_estimate", "N/A")))

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@collections_cmd.command(name="delete")
@click.argument("name")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def delete_collection(name: str, config: str) -> None:
    """Delete a collection."""
    load_cli_db = _resolve("load_cli_db")
    BaseConfig = _resolve("BaseConfig")
    console = _console()
    cfg, db = load_cli_db(config, BaseConfig)

    try:
        db.delete_collection(name)
        console.print(f"[green]Successfully deleted collection '{name}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@collections_cmd.command(name="update-path")
@click.argument("name")
@click.argument("path", type=click.Path(exists=True))
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def update_path(name: str, path: str, config: str) -> None:
    """Update the stored ingest source path for a collection."""
    from pathlib import Path as P

    load_cli_db = _resolve("load_cli_db")
    BaseConfig = _resolve("BaseConfig")
    ChromaDBBackend = _resolve("ChromaDBBackend")
    console = _console()
    cfg, db = load_cli_db(config, BaseConfig)

    if not isinstance(db, ChromaDBBackend):
        console.print("[red]Only supported on ChromaDB backends.[/red]")
        return

    collections = db.list_collections()
    if name not in collections:
        console.print(f"[red]Error:[/red] Collection '{name}' not found.")
        return

    try:
        col = db.get_collection(name)
        resolved = str(P(path).resolve())
        col.modify(metadata={"ingest_source_path": resolved})
        console.print(f"[green]Updated ingest path for '{name}' to: {resolved}[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
