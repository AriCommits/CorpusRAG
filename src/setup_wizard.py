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

    # LLM
    llm_backend: str = "ollama"
    llm_endpoint: str = "http://localhost:11434"
    llm_model: str = "gemma4:26b-a4b-it-q4_K_M"
    llm_api_key: str | None = None
    # Embedding
    embedding_backend: str = "ollama"
    embedding_model: str = "embeddinggemma"
    # Database
    chroma_mode: str = "persistent"
    chroma_host: str | None = None
    chroma_port: int = 8000
    # Paths
    vault_path: str = "./vault"
    # RAG
    rag_strategy: str = "hybrid"
    # Telemetry
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
            # Set endpoint and embedding backend based on selection
            if backend == "ollama":
                self.app.wizard_config.llm_endpoint = "http://localhost:11434"
                self.app.wizard_config.embedding_backend = "ollama"
            elif backend == "openai":
                self.app.wizard_config.llm_endpoint = "https://api.openai.com/v1"
                self.app.wizard_config.embedding_backend = "openai"
            elif backend == "anthropic":
                self.app.wizard_config.llm_endpoint = "https://api.anthropic.com"
                self.app.wizard_config.embedding_backend = "anthropic"
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
            yield Markdown("## Enter ChromaDB server hostname (or leave blank for localhost)")

            with Vertical(id="host-input"):
                yield Input(
                    value="localhost",
                    id="chroma_host_input",
                    placeholder="localhost",
                )

            yield Static()  # Spacer
            yield Button("Back", id="back", variant="default")
            yield Button("Continue", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next":
            host_input = self.query_one("#chroma_host_input", Input)
            host = host_input.value or "localhost"
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

If you selected HTTP mode, start ChromaDB with:
  `docker compose -f .docker/docker-compose.yml up -d`

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
            base_config_path = Path("configs/base.yaml")
            base_config_path.parent.mkdir(parents=True, exist_ok=True)

            wc = self.wizard_config

            config = {
                "llm": {
                    "backend": wc.llm_backend,
                    "endpoint": wc.llm_endpoint,
                    "model": wc.llm_model,
                    "timeout_seconds": 120.0,
                    "temperature": 0.7,
                    "max_tokens": None,
                    "api_key": wc.llm_api_key,
                    "fallback_models": [],
                    "rate_limit_rpm": None,
                    "rate_limit_concurrent": None,
                },
                "embedding": {
                    "backend": wc.embedding_backend,
                    "model": wc.embedding_model,
                    "dimensions": None,
                },
                "database": {
                    "backend": "chromadb",
                    "mode": wc.chroma_mode,
                    "host": wc.chroma_host or "localhost",
                    "port": wc.chroma_port,
                    "persist_directory": "./chroma_store",
                },
                "paths": {
                    "vault": wc.vault_path.replace("\\", "/"),
                    "scratch_dir": "./scratch",
                    "output_dir": "./output",
                },
                "rag": {
                    "strategy": wc.rag_strategy,
                    "chunking": {
                        "child_chunk_size": 400,
                        "child_chunk_overlap": 50,
                        "adaptive": True,
                    },
                    "retrieval": {
                        "top_k_semantic": 50,
                        "top_k_bm25": 50,
                        "top_k_final": 25,
                        "rrf_k": 80,
                    },
                    "parent_store": {
                        "type": "local_file",
                        "path": "./parent_store",
                    },
                    "collection_prefix": "rag",
                },
                "telemetry": {
                    "enabled": wc.telemetry_enabled,
                },
            }

            with open(base_config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            # Generate docker-compose for HTTP mode
            if wc.chroma_mode == "http":
                self._generate_docker_compose(wc)

            # Create required directories
            Path("./parent_store").mkdir(parents=True, exist_ok=True)
            Path("./chroma_store").mkdir(parents=True, exist_ok=True)
            Path(wc.vault_path).mkdir(parents=True, exist_ok=True)

            logger.info(f"Configuration saved to {base_config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def _generate_docker_compose(self, wc) -> None:
        """Generate a minimal docker-compose.yml for ChromaDB."""
        compose_dir = Path(".docker")
        compose_dir.mkdir(parents=True, exist_ok=True)
        compose_file = compose_dir / "docker-compose.yml"

        if compose_file.exists():
            logger.info(f"{compose_file} already exists, skipping generation")
            return

        port = getattr(wc, "chroma_port", 8000)
        compose_content = {
            "services": {
                "chromadb": {
                    "image": "chromadb/chroma:latest",
                    "container_name": "corpus-chromadb",
                    "restart": "unless-stopped",
                    "ports": [f"{port}:8000"],
                    "volumes": ["chroma-data:/chroma/chroma"],
                }
            },
            "volumes": {"chroma-data": None},
        }

        with open(compose_file, "w") as f:
            yaml.dump(compose_content, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated {compose_file} for ChromaDB")

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
