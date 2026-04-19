#!/usr/bin/env python3
"""Interactive TUI setup wizard for CorpusRAG first-time configuration.

Guides new users through:
1. Ollama detection and model setup
2. LLM backend selection (Ollama/OpenAI/Anthropic)
3. ChromaDB mode (local/HTTP)
4. Knowledge base path configuration
5. Telemetry opt-in
6. Test ingest with demo query
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from textual.app import ComposeResult, Screen
from textual.containers import Container, Vertical
from textual.widgets import Button, Input, Label, Markdown, Select, Static

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class WizardConfig:
    """Configuration collected during wizard."""

    llm_backend: str = "ollama"
    llm_model: str = "gemma4:26b-a4b-it-q4_K_M"
    embedding_model: str = "embeddinggemma"
    chroma_mode: str = "persistent"
    chroma_host: str | None = None
    vault_path: str = "./vault"
    telemetry_enabled: bool = False


class WelcomeScreen(Screen):
    """Welcome screen with Ollama detection."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 60;
        height: auto;
        border: solid $accent;
    }

    Button {
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("Welcome to CorpusRAG Setup")
            yield Static()  # Spacer
            yield Markdown("""# CorpusRAG Setup Wizard

Your unified learning and knowledge management toolkit.

This wizard will help you configure:
- LLM backend (Ollama, OpenAI, or Anthropic)
- Vector database (ChromaDB)
- Knowledge base location
- Optional telemetry

Let's get started!
""")
            yield Button("Continue", id="next", variant="primary")
            yield Button("Exit", id="exit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            self.app.push_screen("backend")
        elif event.button.id == "exit":
            self.app.exit()


class BackendScreen(Screen):
    """LLM and embedding backend selection."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 60;
        height: auto;
        border: solid $accent;
    }

    .config-section {
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("LLM Backend Selection")
            yield Static()  # Spacer
            yield Markdown("## Which LLM backend do you prefer?")

            with Vertical(classes="config-section"):
                yield Label("Backend:")
                yield Select(
                    [
                        ("Ollama (Local, Free)", "ollama"),
                        ("OpenAI (API, $)", "openai"),
                        ("Anthropic (API, $)", "anthropic"),
                    ],
                    id="backend_select",
                    value="ollama",
                )

            yield Static()  # Spacer
            yield Button("Back", id="back", variant="default")
            yield Button("Continue", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            select = self.query_one("#backend_select", Select)
            backend = select.value
            self.app.wizard_config.llm_backend = backend
            self.app.push_screen("chroma")


class ChromaScreen(Screen):
    """ChromaDB configuration."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 60;
        height: auto;
        border: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("ChromaDB Configuration")
            yield Static()  # Spacer
            yield Markdown("""## How do you want to store embeddings?

- **Persistent**: Local SQLite database (fast, no extra setup)
- **HTTP**: Connect to ChromaDB server (shared, requires Docker)
""")

            with Vertical(id="mode-select"):
                yield Label("Mode:")
                yield Select(
                    [
                        ("Persistent (Local)", "persistent"),
                        ("HTTP (Docker Server)", "http"),
                    ],
                    id="chroma_mode",
                    value="persistent",
                )

            yield Static()  # Spacer
            yield Button("Back", id="back", variant="default")
            yield Button("Continue", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            mode_select = self.query_one("#chroma_mode", Select)
            mode = mode_select.value
            self.app.wizard_config.chroma_mode = mode

            if mode == "http":
                self.app.push_screen("chroma_host")
            else:
                self.app.push_screen("vault")


class ChromaHostScreen(Screen):
    """ChromaDB HTTP host configuration."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 60;
        height: auto;
        border: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("ChromaDB Server Configuration")
            yield Static()  # Spacer
            yield Markdown("## Enter ChromaDB server address (or leave blank for localhost:8000)")

            with Vertical(id="host-input"):
                yield Input(
                    value="localhost:8000",
                    id="chroma_host_input",
                    placeholder="localhost:8000",
                )

            yield Static()  # Spacer
            yield Button("Back", id="back", variant="default")
            yield Button("Continue", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            host_input = self.query_one("#chroma_host_input", Input)
            host = host_input.value or "localhost:8000"
            self.app.wizard_config.chroma_host = host
            self.app.push_screen("vault")


class VaultScreen(Screen):
    """Knowledge base path configuration."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 60;
        height: auto;
        border: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("Knowledge Base Location")
            yield Static()  # Spacer
            yield Markdown("## Where is your knowledge base located? (markdown files, PDFs, etc.)")

            with Vertical(id="vault-input"):
                yield Input(
                    value="./vault",
                    id="vault_path_input",
                    placeholder="./vault",
                )

            yield Static()  # Spacer
            yield Button("Back", id="back", variant="default")
            yield Button("Continue", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            path_input = self.query_one("#vault_path_input", Input)
            vault_path = path_input.value or "./vault"

            # Create directory if it doesn't exist
            vault = Path(vault_path)
            vault.mkdir(parents=True, exist_ok=True)

            self.app.wizard_config.vault_path = vault_path
            self.app.push_screen("telemetry")


class TelemetryScreen(Screen):
    """Telemetry opt-in."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 60;
        height: auto;
        border: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("Help Improve CorpusRAG")
            yield Static()  # Spacer
            yield Markdown("""## Optional: Share Anonymous Usage Data

We collect:
- Query count (not query content)
- Retrieval latency (not documents)
- Tool usage statistics

We never collect:
- Your documents or knowledge base
- Personal information
- Query text

[Privacy Policy](https://github.com/arian/corpusrag#privacy)
""")

            yield Static()  # Spacer
            yield Button("No Thanks", id="no", variant="default")
            yield Button("Yes, Help", id="yes", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "no":
            self.app.wizard_config.telemetry_enabled = False
            self.app.push_screen("test")
        elif event.button.id == "yes":
            self.app.wizard_config.telemetry_enabled = True
            self.app.push_screen("test")


class TestScreen(Screen):
    """Test ingest and demo query."""

    DEFAULT_CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 80;
        height: auto;
        border: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="content"):
            yield Label("Setup Complete!")
            yield Static()  # Spacer
            yield Markdown("""## Configuration Summary

Your CorpusRAG is now configured and ready to use.

### Next Steps:

1. **Add documents** to your vault directory
2. **Run**: `corpus rag ingest --path ./vault --collection notes`
3. **Query**: `corpus rag ui`

Or use the unified CLI:
- `corpus rag query "your question"` for command-line queries
- `corpus rag ui` for the interactive TUI

---

**Questions?** Check out the [documentation](https://github.com/arian/corpusrag#docs)
""")

            yield Static()  # Spacer
            yield Button("Launch TUI Now", id="launch", variant="primary")
            yield Button("Finish", id="finish", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch":
            self.app.should_launch_tui = True
            self.app.exit()
        elif event.button.id == "finish":
            self.app.exit()


class SetupWizardApp:
    """Non-TUI setup wizard controller (for compatibility)."""

    def __init__(self):
        self.wizard_config = WizardConfig()
        self.should_launch_tui = False

    def run_tui(self) -> bool:
        """Run interactive TUI wizard.

        Returns:
            True if TUI should be launched after setup
        """
        from textual.app import App

        class WizardTUIApp(App):
            """Textual app wrapper for wizard screens."""

            SCREENS = {
                "welcome": WelcomeScreen,
                "backend": BackendScreen,
                "chroma": ChromaScreen,
                "chroma_host": ChromaHostScreen,
                "vault": VaultScreen,
                "telemetry": TelemetryScreen,
                "test": TestScreen,
            }

            def __init__(self, wizard):
                super().__init__()
                self.wizard_config = wizard.wizard_config
                self.should_launch_tui = False

            def on_mount(self) -> None:
                self.push_screen("welcome")

        app = WizardTUIApp(self)
        try:
            app.run()
        except Exception as e:
            logger.error(f"TUI wizard error: {e}")
            return False

        self.should_launch_tui = app.should_launch_tui
        return True

    def save_config(self) -> bool:
        """Save wizard configuration to YAML file.

        Returns:
            True if saved successfully
        """
        try:
            # Load base configuration
            base_config_path = Path("configs/base.yaml")
            if base_config_path.exists():
                with open(base_config_path) as f:
                    config = yaml.safe_load(f)
            else:
                config = {}

            # Update with wizard selections
            if "llm" not in config:
                config["llm"] = {}
            config["llm"]["backend"] = self.wizard_config.llm_backend
            config["llm"]["model"] = self.wizard_config.llm_model

            if "embedding" not in config:
                config["embedding"] = {}
            config["embedding"]["model"] = self.wizard_config.embedding_model

            if "database" not in config:
                config["database"] = {}
            config["database"]["mode"] = self.wizard_config.chroma_mode
            if self.wizard_config.chroma_host:
                config["database"]["host"] = self.wizard_config.chroma_host

            if "paths" not in config:
                config["paths"] = {}
            config["paths"]["vault"] = self.wizard_config.vault_path

            if "telemetry" not in config:
                config["telemetry"] = {}
            config["telemetry"]["enabled"] = self.wizard_config.telemetry_enabled

            # Write configuration
            with open(base_config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Configuration saved to {base_config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def mark_setup_complete(self) -> bool:
        """Create marker file to skip wizard on next run.

        Returns:
            True if marker created successfully
        """
        try:
            marker = Path(".corpus_setup_complete")
            marker.touch()
            return True
        except Exception as e:
            logger.error(f"Failed to create setup marker: {e}")
            return False


def run_setup_wizard() -> int:
    """Run the interactive setup wizard.

    Returns:
        0 on success, 1 on failure
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    wizard = SetupWizardApp()

    # Run TUI wizard
    if not wizard.run_tui():
        logger.error("TUI wizard failed")
        return 1

    # Save configuration
    if not wizard.save_config():
        logger.error("Failed to save configuration")
        return 1

    # Mark setup as complete
    if not wizard.mark_setup_complete():
        logger.error("Failed to create setup marker")
        return 1

    print("\n✓ Setup complete!")
    print("✓ Configuration saved to configs/base.yaml")
    print(f"✓ Vault created at {wizard.wizard_config.vault_path}")

    # Launch TUI if requested
    if wizard.should_launch_tui:
        print("\nLaunching TUI...")
        try:
            from tools.rag.tui import RAGApp

            app = RAGApp()
            app.run()
        except Exception as e:
            logger.error(f"Failed to launch TUI: {e}")
            print("You can launch the TUI manually with: corpus rag ui")

    return 0


def main() -> None:
    """Entry point for corpus-setup command."""
    sys.exit(run_setup_wizard())


if __name__ == "__main__":
    main()
