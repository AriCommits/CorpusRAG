"""Textual screen for managing ChromaDB collections."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

from cli_common import load_cli_db
from config import BaseConfig
from db.chroma import ChromaDBBackend
from tools.rag.slash_commands import SlashCommandResult, slash_command


class CollectionManagerScreen(Screen):
    """Screen for managing vector database collections."""

    BINDINGS = [
        ("q", "quit_screen", "Quit Screen"),
        ("r", "rename_collection", "Rename"),
        ("m", "merge_collections", "Merge"),
        ("d", "delete_collection", "Delete"),
        ("i", "collection_info", "Info"),
    ]

    CSS = """
    CollectionManagerScreen {
        align: center middle;
    }
    #manager-container {
        width: 80%;
        height: 80%;
        border: tall $primary;
        background: $surface;
    }
    DataTable {
        height: 1fr;
    }
    #actions-panel {
        height: auto;
        padding: 1;
        border-top: solid $primary;
    }
    """

    def __init__(self, config_path: str = "configs/base.yaml", *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg, db = load_cli_db(config_path, BaseConfig)
        self.db = db

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="manager-container"):
            yield Label("Collection Management", variant="title")
            yield DataTable(id="collections-table")
            with Vertical(id="actions-panel"):
                yield Label(
                    "Press bindings to act on selected row: r=rename, m=merge, d=delete, i=info, q=quit"
                )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Documents (estimate)", "Exists")
        self.refresh_table()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()

        try:
            collections = self.db.list_collections()
            for name in collections:
                # We can't always quickly get doc count without latency, but let's try
                try:
                    count = self.db.count_documents(name)
                except Exception:
                    count = "Error"
                table.add_row(name, str(count), "Yes", key=name)
        except Exception as e:
            self.notify(f"Error loading collections: {e}", severity="error")

    def action_quit_screen(self) -> None:
        self.app.pop_screen()

    def get_selected_collection(self) -> str | None:
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate)
                return row_key.row_key.value
            except Exception:
                pass
        return None

    def action_collection_info(self) -> None:
        col = self.get_selected_collection()
        if not col:
            self.notify("No collection selected", severity="warning")
            return

        if not isinstance(self.db, ChromaDBBackend):
            self.notify(
                "Stats are only supported on ChromaDB backends", severity="warning"
            )
            return

        try:
            stats = self.db.get_collection_stats(col)
            self.notify(
                f"Info for {col}:\nDocs: {stats['doc_count']}, Chunks: {stats['chunk_count']}\n"
                f"Unique Files: {stats['unique_files']}, Size: {stats['size_estimate']} bytes",
                timeout=10,
            )
        except Exception as e:
            self.notify(f"Error getting info: {e}", severity="error")

    def action_delete_collection(self) -> None:
        col = self.get_selected_collection()
        if not col:
            self.notify("No collection selected", severity="warning")
            return

        try:
            self.db.delete_collection(col)
            self.notify(f"Deleted collection '{col}'")
            self.refresh_table()
        except Exception as e:
            self.notify(f"Error deleting collection: {e}", severity="error")

    # Rename and merge could prompt for inputs using a modal, but for simplicity we
    # will handle basic notifications or implement a minimal input prompt later.
    def action_rename_collection(self) -> None:
        self.notify("Rename feature from TUI requires an input dialog (coming soon!)")

    def action_merge_collections(self) -> None:
        self.notify("Merge feature from TUI requires an input dialog (coming soon!)")


@slash_command("collections", "Manage database collections via TUI")
def handle_collections_slash(args: list[str]) -> SlashCommandResult:
    return SlashCommandResult(type="screen", screen=CollectionManagerScreen())


@slash_command("collection", "Alias for /collections")
def handle_collection_alias_slash(args: list[str]) -> SlashCommandResult:
    return SlashCommandResult(type="screen", screen=CollectionManagerScreen())


@slash_command("switch", "Switch to a different collection. Usage: /switch <name>")
def handle_switch_slash(args: list[str]) -> SlashCommandResult:
    if not args:
        return SlashCommandResult(
            type="error",
            content="Please provide a collection name. Example: /switch my_docs",
        )
    target = args[0]

    # We should update app's collection here, but we don't have direct access to app.
    # Textual's app state modification via command return might be needed.
    # For now, we will return a toast. The actual app state switch might need to be
    # intercepted in `handle_slash_result` in RAGApp.
    return SlashCommandResult(type="toast", toast_message=f"switch_collection:{target}")
