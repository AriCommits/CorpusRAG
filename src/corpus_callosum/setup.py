"""Setup wizard for CorpusCallosum initialization."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from .config import PROJECT_ROOT


def _color(text: str, code: str) -> str:
    """Apply ANSI color code if terminal supports it."""
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text: str) -> str:
    return _color(text, "32")


def yellow(text: str) -> str:
    return _color(text, "33")


def red(text: str) -> str:
    return _color(text, "31")


def blue(text: str) -> str:
    return _color(text, "34")


def bold(text: str) -> str:
    return _color(text, "1")


def print_banner() -> None:
    """Print the setup wizard banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   CorpusCallosum Setup Wizard                                ║
║   ─────────────────────────────                              ║
║   Local RAG service with hybrid retrieval                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(blue(banner))


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt the user for a yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{question} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print(yellow("Please enter 'y' or 'n'."))


def prompt_string(prompt: str, default: str | None = None) -> str:
    """Prompt the user for a string value."""
    if default:
        display_prompt = f"{prompt} [{default}]: "
    else:
        display_prompt = f"{prompt}: "

    while True:
        response = input(display_prompt).strip()
        if response:
            return response
        if default is not None:
            return default
        print(yellow("This field is required."))


def prompt_int(prompt: str, default: int) -> int:
    """Prompt the user for an integer value."""
    while True:
        response = input(f"{prompt} [{default}]: ").strip()
        if not response:
            return default
        try:
            return int(response)
        except ValueError:
            print(yellow("Please enter a valid integer."))


def check_ollama() -> tuple[bool, str | None]:
    """Check if Ollama is installed and running."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, None
    except FileNotFoundError:
        return False, None
    except subprocess.TimeoutExpired:
        return False, None


def setup_config() -> tuple[Path | None, bool]:
    """Interactive setup for configuration file.

    Returns:
        Tuple of (config_path, use_docker_chroma).
        config_path is None if setup failed.
    """
    print(bold("\n📋 Configuration Setup\n"))

    config_dir = PROJECT_ROOT / "configs"
    config_path = config_dir / "corpus_callosum.yaml"
    example_path = config_dir / "corpus_callosum.yaml.example"

    # Check if config already exists
    if config_path.exists():
        print(f"Configuration file already exists at: {config_path}")
        if not prompt_yes_no("Do you want to overwrite it?", default=False):
            print(green("✓ Keeping existing configuration."))
            # Check existing config to determine if Docker mode
            with config_path.open(encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
            use_docker = existing.get("chroma", {}).get("mode") == "http"
            return config_path, use_docker

    # Check if example exists
    if not example_path.exists():
        print(red(f"✗ Example config not found at: {example_path}"))
        print("  Please ensure you have the complete repository.")
        return None, False

    # Build configuration interactively
    print("\nLet's configure CorpusCallosum:\n")

    config_data: dict = {}

    # Paths configuration
    print(bold("─── Paths ───"))
    vault_path = prompt_string(
        "Document vault directory (for storing your documents)", default="./vault"
    )
    config_data["paths"] = {
        "vault": vault_path,
        "chromadb_store": "./chroma_store",
    }

    # Model configuration
    print(bold("\n─── LLM Configuration ───"))

    ollama_running, ollama_output = check_ollama()
    if ollama_running:
        print(green("✓ Ollama detected and running!"))
        if ollama_output:
            print("  Available models:")
            for line in ollama_output.strip().split("\n")[1:5]:  # Show first 4 models
                print(f"    {line}")
    else:
        print(yellow("⚠ Ollama not detected."))
        print("  Please install Ollama from https://ollama.ai")
        print("  Or configure a different LLM endpoint below.")

    endpoint = prompt_string("LLM API endpoint", default="http://localhost:11434")
    model_name = prompt_string("Model name", default="llama3")

    config_data["model"] = {
        "endpoint": endpoint,
        "name": model_name,
        "timeout_seconds": 120.0,
        "max_flashcard_context_chars": 12000,
    }

    # Server configuration
    print(bold("\n─── Server Configuration ───"))
    host = prompt_string("Server host", default="0.0.0.0")
    port = prompt_int("Server port", default=8080)

    config_data["server"] = {
        "host": host,
        "port": port,
    }

    # ChromaDB configuration
    print(bold("\n─── ChromaDB Storage ───"))
    print("ChromaDB stores your document embeddings. Choose how to run it:\n")
    print(f"  {bold('1. Local (recommended for personal use)')}")
    print("     - No Docker required")
    print("     - Data stored in ./chroma_store/ folder")
    print("     - Simple setup, works out of the box\n")
    print(f"  {bold('2. Docker (recommended for production/servers)')}")
    print("     - Requires Docker to be installed")
    print("     - Runs ChromaDB as a separate service")
    print("     - Better for multi-user or containerized deployments\n")

    use_docker = prompt_yes_no("Use Docker for ChromaDB?", default=False)

    if use_docker:
        config_data["chroma"] = {
            "mode": "http",
            "host": "chroma",
            "port": 8000,
            "ssl": False,
        }
    else:
        config_data["chroma"] = {
            "mode": "persistent",
        }

    # Embedding model configuration
    print(bold("\n─── Embedding Model ───"))
    print("Embeddings convert your documents into vectors for semantic search.\n")
    print(f"  {bold('1. all-MiniLM-L6-v2')} (default)")
    print("     - 384 dimensions, ~80MB download")
    print("     - Fast and lightweight\n")
    print(f"  {bold('2. all-mpnet-base-v2')}")
    print("     - 768 dimensions, ~420MB download")
    print("     - Higher quality, slower\n")

    use_larger_model = prompt_yes_no("Use the larger, higher-quality model?", default=False)

    if use_larger_model:
        embedding_model = "sentence-transformers/all-mpnet-base-v2"
    else:
        embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

    config_data["embedding"] = {
        "model": embedding_model,
    }

    # Advanced options
    print(bold("\n─── Advanced Options ───"))
    if prompt_yes_no("Configure advanced options (chunking, retrieval)?", default=False):
        print("\nChunking settings affect how documents are split:")
        chunk_size = prompt_int("Chunk size (characters)", default=500)
        chunk_overlap = prompt_int("Chunk overlap (characters)", default=50)

        config_data["chunking"] = {
            "size": chunk_size,
            "overlap": chunk_overlap,
        }

        print("\nRetrieval settings affect search quality:")
        top_k = prompt_int("Number of results to return", default=5)

        config_data["retrieval"] = {
            "top_k_semantic": 10,
            "top_k_bm25": 10,
            "top_k_final": top_k,
            "rrf_k": 60,
        }

    # Write configuration
    print(bold("\n─── Saving Configuration ───"))

    config_dir.mkdir(parents=True, exist_ok=True)

    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    print(green(f"✓ Configuration saved to: {config_path}"))
    return config_path, use_docker


def setup_directories(config_path: Path) -> bool:
    """Create required directories."""
    print(bold("\n📁 Directory Setup\n"))

    # Load the config to get paths
    with config_path.open(encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}

    paths = config_data.get("paths", {})
    vault_path = Path(paths.get("vault", "./vault"))
    chroma_path = Path(paths.get("chromadb_store", "./chroma_store"))

    # Resolve relative paths
    if not vault_path.is_absolute():
        vault_path = PROJECT_ROOT / vault_path
    if not chroma_path.is_absolute():
        chroma_path = PROJECT_ROOT / chroma_path

    # Create directories
    for path, name in [(vault_path, "Vault"), (chroma_path, "ChromaDB store")]:
        if path.exists():
            print(f"  {name}: {green('exists')} at {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  {name}: {green('created')} at {path}")

    return True


def generate_password(length: int = 16) -> str:
    """Generate a random password."""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def setup_docker() -> bool:
    """Setup Docker configuration if needed."""
    print(bold("\n🐳 Docker Setup\n"))

    docker_config = PROJECT_ROOT / "configs" / "corpus_callosum.docker.yaml"
    docker_example = PROJECT_ROOT / "configs" / "corpus_callosum.docker.yaml.example"
    env_file = PROJECT_ROOT / "configs" / ".env"

    # Setup docker config
    config_created = False
    if docker_config.exists():
        print(f"  Docker config: {green('exists')} at {docker_config}")
        config_created = True
    elif docker_example.exists():
        if prompt_yes_no("Create Docker configuration from example?", default=True):
            shutil.copy(docker_example, docker_config)
            print(f"  Docker config: {green('created')} at {docker_config}")
            config_created = True
    else:
        print(yellow("  Docker example config not found, skipping."))

    if not config_created:
        return False

    # Setup .env file for Docker secrets
    print(bold("\n─── Docker Environment ───"))
    print("Docker requires a .env file for database credentials.\n")

    if env_file.exists():
        print(f"  Environment file: {green('exists')} at {env_file}")
        if not prompt_yes_no("Do you want to overwrite it?", default=False):
            return True

    # Generate or prompt for password
    default_password = generate_password()
    print("\nPostgres is used for observability (traces storage).")

    postgres_user = prompt_string("Postgres username", default="otel")

    use_generated = prompt_yes_no("Generate a secure random password? (recommended)", default=True)
    if use_generated:
        postgres_password = default_password
        print(f"  Generated password: {yellow(postgres_password)}")
        print(f"  {yellow('Save this password if you need to access Postgres directly.')}")
    else:
        postgres_password = prompt_string("Postgres password")

    postgres_db = prompt_string("Postgres database", default="otel_traces")

    # Write .env file
    env_content = f"""# CorpusCallosum Docker Environment
# Generated by corpus-setup. DO NOT commit to version control.

# Postgres (observability backend)
POSTGRES_USER={postgres_user}
POSTGRES_PASSWORD={postgres_password}
POSTGRES_DB={postgres_db}
"""

    env_file.write_text(env_content, encoding="utf-8")
    print(f"\n  Environment file: {green('created')} at {env_file}")

    return True


def print_next_steps(use_docker_chroma: bool) -> None:
    """Print next steps for the user."""
    print(bold("\n" + "═" * 60))
    print(bold("✅ Setup Complete!"))
    print("═" * 60)

    print(bold("\n📖 Next Steps:\n"))

    if use_docker_chroma:
        print("1. " + bold("Start Docker services:"))
        print("   " + blue("docker compose -f .docker/docker-compose.yml up -d"))
        print()
        print("2. " + bold("Add documents to your vault:"))
        print("   Copy .md, .pdf, or .txt files to the vault directory\n")
        print("3. " + bold("Ingest documents (via API):"))
        print("   " + blue("curl -X POST http://localhost:8080/ingest \\"))
        print("        -H 'Content-Type: application/json' \\")
        print('        -d \'{"file_path": "./vault/my_docs", "collection": "my_collection"}\'')
        print()
    else:
        print("1. " + bold("Ingest documents (CLI):"))
        print("   " + blue("corpus-ingest --path ./vault/my_docs --collection my_collection"))
        print()
        print("2. " + bold("Query your documents (CLI):"))
        print("   " + blue("corpus-query --collection my_collection"))
        print("   Then type your question at the prompt.\n")
        print("3. " + bold("Or start the API server:"))
        print("   " + blue("corpus-api"))
        print()

    print(bold("📚 Documentation:"))
    print("   See README.md for more detailed usage instructions.\n")


def main() -> int:
    """Run the setup wizard."""
    print_banner()

    print("This wizard will help you set up CorpusCallosum.\n")

    if not prompt_yes_no("Ready to begin?", default=True):
        print("\nSetup cancelled. Run 'corpus-setup' when ready.")
        return 0

    # Step 1: Configuration
    config_path, use_docker_chroma = setup_config()
    if not config_path:
        print(red("\n✗ Setup failed during configuration."))
        return 1

    # Step 2: Directories
    if not setup_directories(config_path):
        print(red("\n✗ Setup failed during directory creation."))
        return 1

    # Step 3: Docker (optional) - only if user chose Docker mode
    if use_docker_chroma:
        setup_docker()

    # Final steps
    print_next_steps(use_docker_chroma)

    return 0


if __name__ == "__main__":
    sys.exit(main())
