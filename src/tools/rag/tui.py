"""Terminal User Interface for RAG tool using Textual."""

from datetime import datetime

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Markdown, Static

from .agent import RAGAgent


class SessionItem(ListItem):
    """A list item representing a session."""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        yield Label(self.session_id)


class ChatMessage(Static):
    """A widget to display a chat message."""

    def __init__(self, role: str, content: str):
        super().__init__()
        self.role = role
        self.content = content

    def compose(self) -> ComposeResult:
        prefix = "### You" if self.role == "user" else "### Assistant"
        yield Markdown(f"{prefix}\n\n{self.content}")


class RAGApp(App):
    """Textual RAG Application."""

    CSS = """
    Screen {
        layers: sidebar main;
    }

    #sidebar {
        width: 30;
        background: $surface;
        border-right: tall $primary;
        height: 100%;
    }

    #main-chat {
        height: 100%;
        padding: 1 2;
    }

    #chat-log {
        height: 1fr;
        overflow-y: scroll;
    }

    #input-container {
        height: auto;
        border-top: tall $primary;
        padding: 1;
    }

    .user-message {
        background: $primary-darken-2;
        margin: 1 0;
        padding: 1;
    }

    .assistant-message {
        background: $surface-lighten-1;
        margin: 1 0;
        padding: 1;
    }
    """

    def __init__(self, agent: RAGAgent, collection: str):
        super().__init__()
        self.agent = agent
        self.collection = collection
        self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("  Filters", variant="title")
                yield Input(placeholder="Tags (comma separated)", id="tag-input")
                yield Input(
                    placeholder="Sections (comma separated)", id="section-input"
                )
                yield Label("  Sessions", variant="title")
                yield ListView(id="session-list")
            with Vertical(id="main-chat"):
                yield Vertical(id="chat-log")
                with Vertical(id="input-container"):
                    yield Input(placeholder="Ask a question...", id="user-input")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app."""
        self.refresh_sessions()
        self.load_session(self.current_session_id)

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
        chat_log = self.query_one("#chat-log", Vertical)

        # Clear existing messages
        for child in chat_log.children:
            child.remove()

        history = self.agent.session_manager.load_session(session_id)
        for msg in history:
            chat_log.mount(ChatMessage(msg["role"], msg["content"]))

        # Scroll to bottom
        chat_log.scroll_end(animate=False)

    @on(Input.Submitted, "#user-input")
    def handle_submit(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        message = event.value.strip()
        if not message:
            return

        # Clear input
        event.input.value = ""

        # Get current filters from sidebar
        tags_raw = self.query_one("#tag-input", Input).value.strip()
        sections_raw = self.query_one("#section-input", Input).value.strip()

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        sections = (
            [s.strip() for s in sections_raw.split(",") if s.strip()]
            if sections_raw
            else []
        )

        # Display user message immediately
        chat_log = self.query_one("#chat-log", Vertical)
        chat_log.mount(ChatMessage("user", message))
        chat_log.scroll_end()

        # Generate assistant response asynchronously
        self.generate_response(message, tags, sections)

    @work(exclusive=True, thread=True)
    def generate_response(
        self, message: str, tags: list[str], sections: list[str]
    ) -> None:
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
        chat_log = self.query_one("#chat-log", Vertical)
        chat_log.mount(ChatMessage("assistant", response))
        chat_log.scroll_end()

        # Refresh session list in case it's a new session
        self.refresh_sessions()

    @on(ListView.Selected, "#session-list")
    def on_session_selected(self, event: ListView.Selected) -> None:
        """Switch to a different session."""
        if isinstance(event.item, SessionItem):
            self.load_session(event.item.session_id)
