"""Terminal User Interface for RAG tool using Textual."""

import re
import time
from datetime import datetime

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
    Switch,
)

from .agent import RAGAgent
from .slash_commands import SlashCommandResult, SlashCommandRouter


class SessionItem(ListItem):
    """A list item representing a session."""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        yield Label(self.session_id)


class ChatMessage(Static):
    """A widget to display a chat message with optional inclusion toggle."""

    DEFAULT_CSS = """
    ChatMessage {
        margin: 0 0 1 0;
        height: auto;
    }

    ChatMessage.excluded {
        opacity: 0.5;
        border-left: solid $warning;
    }

    ChatMessage > Horizontal {
        height: auto;
    }

    ChatMessage #message-content {
        width: 1fr;
    }

    ChatMessage #include-toggle {
        width: auto;
        margin: 0 1 0 1;
    }
    """

    included_in_context = reactive(True)

    def __init__(self, role: str, content: str, included: bool = True):
        super().__init__()
        self.role = role
        self.content = content
        self.included_in_context = included

    def compose(self) -> ComposeResult:
        prefix = "### You" if self.role == "user" else "### Assistant"
        with Horizontal():
            yield Markdown(f"{prefix}\n\n{self.content}", id="message-content")
            yield Switch(value=self.included_in_context, id="include-toggle")

    def watch_included_in_context(self, value: bool) -> None:
        """Update CSS class based on inclusion status."""
        if value:
            self.remove_class("excluded")
        else:
            self.add_class("excluded")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle toggle change and show undo toast if excluding."""
        self.included_in_context = event.value
        # Show undo notification when message is excluded
        if not event.value:
            self.app.notify("Message excluded from context [Click to undo]", timeout=3.0)
            # Check context warning after exclusion
            self.app._check_context_warning()
        self.post_message(self.InclusionToggled(self, event.value))

    class InclusionToggled(Message):
        """Posted when message inclusion is toggled."""

        def __init__(self, message: "ChatMessage", included: bool) -> None:
            super().__init__()
            self.message = message
            self.included = included


def _validate_message_id(message_id: str) -> bool:
    """Validate message ID format (UUID only).

    Args:
        message_id: Message identifier to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    return bool(re.match(r"^[a-f0-9\-]{36}$", message_id))


class RAGApp(App):
    """Textual RAG Application."""

    BINDINGS = [
        ("f2", "manage_collections", "Collections [F2]"),
        ("f5", "sync", "Sync [F5]"),
        ("f1", "show_help", "Help [F1]"),
    ]

    CSS = """
    #sidebar {
        width: 30;
        background: $surface;
        border-right: tall $primary;
        height: 100%;
    }

    .sidebar-title {
        text-style: bold;
        margin: 1 0 0 1;
        color: $accent;
    }

    #sync-status {
        margin: 0 0 1 2;
        color: $text-muted;
    }

    #strategy-label {
        margin: 0 0 1 2;
        color: $text-muted;
    }

    #main-chat {
        height: 100%;
        padding: 1 2;
    }

    #chat-log {
        height: 1fr;
        min-height: 5;
    }

    #input-container {
        height: auto;
        dock: bottom;
        padding: 0 1;
    }

    ChatMessage {
        margin: 0 0 1 0;
        height: auto;
    }

    .context-warning {
        background: $warning;
    }
    """

    def __init__(self, agent: RAGAgent, collection: str):
        super().__init__()
        self.agent = agent
        self.collection = collection
        self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.router = SlashCommandRouter()
        self._last_context_sync = 0.0  # Rate limiting for context toggle sync

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Sync Status", classes="sidebar-title")
                yield Label("Unknown", id="sync-status")
                yield Label("Strategy", classes="sidebar-title")
                yield Label("hybrid", id="strategy-label")
                yield Label("Filters", classes="sidebar-title")
                yield Input(placeholder="Tags (comma separated)", id="tag-input")
                yield Input(placeholder="Sections (comma separated)", id="section-input")
                yield Label("Sessions", classes="sidebar-title")
                yield ListView(id="session-list")
            with Vertical(id="main-chat"):
                yield VerticalScroll(id="chat-log")
                with Vertical(id="input-container"):
                    yield Input(
                        placeholder="Ask a question... (type /help for commands)", id="user-input"
                    )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app."""
        self.refresh_sessions()
        self.load_session(self.current_session_id)
        # Update footer with current strategy
        self._update_footer_strategy()
        # Initial sync check (dry-run)
        self.run_sync(dry_run=True)

    def _update_footer_strategy(self) -> None:
        """Update footer and sidebar to show current retrieval strategy."""
        footer = self.query_one(Footer)
        strategy = getattr(self.agent.config.rag, "strategy", "hybrid")
        footer.update(f"Strategy: {strategy} | Collection: {self.collection}")

    def _update_strategy_label(self, strategy: str) -> None:
        """Update strategy label in sidebar.

        Args:
            strategy: New strategy name
        """
        try:
            strategy_label = self.query_one("#strategy-label", Label)
            strategy_label.update(strategy)
        except Exception:
            pass  # Widget may not be mounted yet

    def _rate_limited_context_sync(self, delay: float = 0.1) -> bool:
        """Rate limit context toggle sync to prevent UI lag.

        Args:
            delay: Minimum time (seconds) between context syncs

        Returns:
            True if enough time has passed, False otherwise
        """
        now = time.time()
        if now - self._last_context_sync >= delay:
            self._last_context_sync = now
            return True
        return False

    def _calculate_context_usage(self) -> float:
        """Calculate context window usage percentage.

        Returns:
            Percentage of context window used (0-100)
        """
        history = self.agent.session_manager.load_session(self.current_session_id)
        # Simple heuristic: estimate tokens based on message count
        # Typical context window: ~4000 tokens, ~100-200 tokens per message
        max_context_messages = 40
        included_count = sum(1 for msg in history if msg.get("included", True))
        return min(100, (included_count / max_context_messages) * 100)

    def _check_context_warning(self) -> None:
        """Check and update context warning if usage > 80%."""
        usage = self._calculate_context_usage()
        if usage > 80:
            # Show warning toast
            self.notify(f"⚠️  Context window at {usage:.0f}%", severity="warning", timeout=3.0)

    def refresh_sessions(self) -> None:
        """Refresh the session list."""
        session_list = self.query_one("#session-list", ListView)
        session_list.clear()
        sessions = self.agent.session_manager.list_sessions()
        for session_id in sorted(sessions, reverse=True):
            session_list.append(SessionItem(session_id))

    def load_session(self, session_id: str) -> None:
        """Load a session's history into the chat log."""
        self.current_session_id = session_id
        chat_log = self.query_one("#chat-log", VerticalScroll)

        # Clear existing messages
        for child in list(chat_log.children):
            child.remove()

        history = self.agent.session_manager.load_session(session_id)
        for msg in history:
            included = msg.get("included", True)
            chat_log.mount(ChatMessage(msg["role"], msg["content"], included=included))

        # Scroll to bottom
        chat_log.scroll_end(animate=False)

        # Check context warning after loading session
        self._check_context_warning()

    @on(Input.Submitted, "#user-input")
    def handle_submit(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        message = event.value.strip()
        if not message:
            return

        # Clear input
        event.input.value = ""

        # Handle slash commands
        if self.router.is_slash_command(message):
            result = self.router.dispatch(self.router.parse(message))
            self.handle_slash_result(result)
            return

        # Get current filters from sidebar
        tags_raw = self.query_one("#tag-input", Input).value.strip()
        sections_raw = self.query_one("#section-input", Input).value.strip()

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        sections = [s.strip() for s in sections_raw.split(",") if s.strip()] if sections_raw else []

        # Display user message immediately
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(ChatMessage("user", message, included=True))
        chat_log.scroll_end()

        # Generate assistant response asynchronously
        self.generate_response(message, tags, sections)

    def handle_slash_result(self, result: SlashCommandResult) -> None:
        """Process the result of a slash command."""
        if result.type == "text" or result.type == "error":
            chat_log = self.query_one("#chat-log", VerticalScroll)
            chat_log.mount(ChatMessage("assistant", result.content or "", included=True))
            chat_log.scroll_end()
        elif result.type == "toast":
            msg = result.toast_message or ""
            if msg.startswith("switch_collection:"):
                new_col = msg.split(":", 1)[1]
                self.collection = new_col
                self.notify(f"Switched collection to: {new_col}")
                # Refresh session id for new collection
                self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.load_session(self.current_session_id)
                # Refresh sync status for new collection
                self.run_sync(dry_run=True)
            elif msg.startswith("sync:"):
                action = msg.split(":", 1)[1]
                if action == "full":
                    self.run_sync(dry_run=False)
                elif action == "dry-run" or action == "status":
                    self.run_sync(dry_run=True)
            elif msg.startswith("export:"):
                fmt = msg.split(":", 1)[1]
                self.notify(f"Exporting to {fmt}... (Feature implementation in progress)")
            elif msg.startswith("filter:"):
                filter_val = msg.split(":", 1)[1]
                tag_input = self.query_one("#tag-input", Input)
                if filter_val == "clear":
                    tag_input.value = ""
                    self.notify("Filters cleared")
                else:
                    tag_input.value = filter_val
                    self.notify(f"Filter set: {filter_val}")
            elif msg.startswith("strategy:"):
                strategy_name = msg.split(":", 1)[1]
                self._update_strategy_label(strategy_name)
                self.notify(f"Strategy switched to: {strategy_name}")
            else:
                self.notify(msg)
                if msg == "Chat history cleared":
                    self.agent.session_manager.delete_session(self.current_session_id)
                    self.load_session(self.current_session_id)
        elif result.type == "stream":
            # For stream, treat it as a regular message
            tags_raw = self.query_one("#tag-input", Input).value.strip()
            sections_raw = self.query_one("#section-input", Input).value.strip()
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
            sections = (
                [s.strip() for s in sections_raw.split(",") if s.strip()] if sections_raw else []
            )

            chat_log = self.query_one("#chat-log", VerticalScroll)
            chat_log.mount(ChatMessage("user", result.content or "", included=True))
            chat_log.scroll_end()
            self.generate_response(result.content or "", tags, sections)
        elif result.type == "screen" and result.screen:
            self.push_screen(result.screen)

    def action_manage_collections(self) -> None:
        """Open collection manager screen."""
        from .tui_collections import CollectionManagerScreen

        self.push_screen(CollectionManagerScreen())

    def action_sync(self) -> None:
        """Run full sync."""
        self.run_sync(dry_run=False)

    def action_show_help(self) -> None:
        """Show help with available commands."""
        result = self.router.dispatch(self.router.parse("/help"))
        self.handle_slash_result(result)

    def update_sync_status(self, status: str) -> None:
        """Update the sync status label."""
        self.query_one("#sync-status", Label).update(status)

    @work(exclusive=True, thread=True)
    def run_sync(self, dry_run: bool = False) -> None:
        """Run sync in background."""
        from .sync import RAGSyncer

        self.call_from_thread(
            self.update_sync_status, "Syncing..." if not dry_run else "Checking..."
        )

        try:
            syncer = RAGSyncer(self.agent.config, self.agent.db)
            # Use vault path from config
            vault_path = self.agent.config.paths.vault
            res = syncer.sync(vault_path, self.collection, dry_run=dry_run)

            status = f"{len(res.new_files)}N, {len(res.modified_files)}M, {len(res.deleted_files)}D"
            if not dry_run:
                status += f" (+{res.chunks_added})"

            self.call_from_thread(self.update_sync_status, status)
            if not dry_run:
                self.notify(f"Sync complete: {status}")
        except Exception as e:
            self.call_from_thread(self.update_sync_status, f"Error: {e}")

    @work(exclusive=True, thread=True)
    def generate_response(self, message: str, tags: list[str], sections: list[str]) -> None:
        """Generate response from RAG agent in a background thread."""
        self.sub_title = "Thinking..."

        # Build where filter
        where = None
        if tags or sections:
            tag_filter = None
            if tags:
                if len(tags) == 1:
                    tag_filter = {"tags": {"$contains": tags[0]}}
                else:
                    tag_filter = {"$or": [{"tags": {"$contains": t}} for t in tags]}

            section_filter = None
            if sections:
                section_filter = {
                    "$or": [
                        {"Document Title": {"$in": sections}},
                        {"Subsection": {"$in": sections}},
                    ]
                }

            if tag_filter and section_filter:
                where = {"$and": [tag_filter, section_filter]}
            elif tag_filter:
                where = tag_filter
            else:
                where = section_filter

        # Run blocking agent call
        try:
            response = self.agent.chat(
                message,
                self.collection,
                session_id=self.current_session_id,
                where=where,
            )
            # Update UI from thread
            self.call_from_thread(self.display_response, response)
        except Exception as e:
            self.call_from_thread(self.display_response, f"Error: {e}")

    def display_response(self, response: str) -> None:
        """Display response and cleanup."""
        self.sub_title = ""
        from utils.benchmarking import benchmarker

        latency_info = ""
        if benchmarker.history:
            last = benchmarker.history[-1]
            latency_info = f"\n\n*({last.total_ms:.0f}ms)*"

        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(ChatMessage("assistant", f"{response}{latency_info}", included=True))
        chat_log.scroll_end()

        # Refresh session list in case it's a new session
        self.refresh_sessions()

    @on(ListView.Selected, "#session-list")
    def on_session_selected(self, event: ListView.Selected) -> None:
        """Switch to a different session."""
        if isinstance(event.item, SessionItem):
            self.load_session(event.item.session_id)
