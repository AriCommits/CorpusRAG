"""CLI commands for managing ChromaDB collections."""

import click
from rich.console import Console
from rich.table import Table

from cli_common import load_cli_db
from config import BaseConfig
from db.chroma import ChromaDBBackend

console = Console()


@click.group(name="collections")
def collections_cmd() -> None:
    """Manage vector database collections."""


@collections_cmd.command(name="list")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def list_collections(config: str) -> None:
    """List all available collections."""
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
    cfg, db = load_cli_db(config, BaseConfig)

    if not isinstance(db, ChromaDBBackend):
        console.print("[red]Stats are only supported on ChromaDB backends.[/red]")
        return

    # Check collection exists
    collections = db.list_collections()
    if name not in collections:
        console.print(f"[red]Error:[/red] Collection '{name}' not found.")
        console.print(f"Available collections: {', '.join(collections) if collections else '(none)'}")
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
    cfg, db = load_cli_db(config, BaseConfig)

    try:
        db.delete_collection(name)
        console.print(f"[green]Successfully deleted collection '{name}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@collections_cmd.command(name="manage")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def manage_collections(config: str) -> None:
    """Launch TUI for managing collections."""
    from textual.app import App

    from tools.rag.tui_collections import CollectionManagerScreen

    class CollectionManagerApp(App[None]):
        def on_mount(self) -> None:
            self.push_screen(CollectionManagerScreen(config_path=config))

    app = CollectionManagerApp()
    app.run()
