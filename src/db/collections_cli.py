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
        stats = db.get_collection_stats(c.name)
        table.add_row(
            c.name,
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

    try:
        stats = db.get_collection_stats(name)

        table = Table(title=f"Stats for: {name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Document Count", str(stats["doc_count"]))
        table.add_row("Chunk Count", str(stats["chunk_count"]))
        table.add_row("Unique Files", str(stats["unique_files"]))
        table.add_row("Estimated Size (bytes)", str(stats["size_estimate"]))

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@collections_cmd.command(name="rename")
@click.argument("old_name")
@click.argument("new_name")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def rename_collection(old_name: str, new_name: str, config: str) -> None:
    """Rename a collection."""
    cfg, db = load_cli_db(config, BaseConfig)

    if not isinstance(db, ChromaDBBackend):
        console.print("[red]Rename is only supported on ChromaDB backends.[/red]")
        return

    try:
        col = db.get_collection(old_name)
        col.modify(name=new_name)
        console.print(
            f"[green]Successfully renamed '{old_name}' to '{new_name}'.[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@collections_cmd.command(name="merge")
@click.argument("source", nargs=-1)
@click.argument("destination")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def merge_collections(source: tuple[str, ...], destination: str, config: str) -> None:
    """Merge source collections into destination collection."""
    cfg, db = load_cli_db(config, BaseConfig)

    if not isinstance(db, ChromaDBBackend):
        console.print("[red]Merge is only supported on ChromaDB backends.[/red]")
        return

    try:
        try:
            dest_col = db.get_collection(destination)
        except Exception:
            db.create_collection(destination)
            dest_col = db.get_collection(destination)

        total_merged = 0
        for src in source:
            source_col = db.get_collection(src)
            data = source_col.get(include=["metadatas", "documents", "embeddings"])

            if data["ids"]:
                # Check for embeddings because it can be None if not computed or disabled
                if data["embeddings"] is not None:
                    dest_col.add(
                        ids=data["ids"],
                        documents=data["documents"],
                        metadatas=data["metadatas"],
                        embeddings=data["embeddings"],
                    )
                else:
                    dest_col.add(
                        ids=data["ids"],
                        documents=data["documents"],
                        metadatas=data["metadatas"],
                    )
                console.print(
                    f"[green]Successfully merged {len(data['ids'])} items from '{src}' to '{destination}'.[/green]"
                )
                total_merged += len(data["ids"])
            else:
                console.print(f"Source collection '{src}' is empty.")
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
