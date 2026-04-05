"""Package entry point for running corpus_callosum as a module.

This enables platform-agnostic CLI usage:

    python -m corpus_callosum <command> [args...]

Available commands:
    ask          - Query a collection (corpus-ask)
    flashcards   - Generate flashcards (corpus-flashcards)
    collections  - List collections (corpus-collections)
    ingest       - Ingest documents (corpus-ingest)
    convert      - Convert document formats (corpus-convert)
    api          - Start the API server (corpus-api)
    setup        - Run initial setup (corpus-setup)

Examples:
    python -m corpus_callosum collections
    python -m corpus_callosum ask -c mycollection "What is X?"
    python -m corpus_callosum ingest ./docs -c mycollection
    python -m corpus_callosum convert ./docs --scan
"""

from __future__ import annotations

import sys


def main() -> None:
    """Route to the appropriate CLI command."""
    if len(sys.argv) < 2:
        print("Usage: python -m corpus_callosum <command> [args...]")
        print()
        print("Available commands:")
        print("  ask          Query a collection")
        print("  flashcards   Generate flashcards from a collection")
        print("  collections  List all collections")
        print("  ingest       Ingest documents into a collection")
        print("  convert      Convert document formats to Markdown")
        print("  api          Start the API server")
        print("  setup        Run initial setup")
        print()
        print("Examples:")
        print("  python -m corpus_callosum collections")
        print('  python -m corpus_callosum ask -c docs "What is X?"')
        print("  python -m corpus_callosum ingest ./docs -c docs")
        sys.exit(1)

    command = sys.argv[1]
    # Remove the command from argv so subcommands see correct args
    sys.argv = [f"corpus-{command}", *sys.argv[2:]]

    if command == "ask":
        from .cli import ask_main

        ask_main()
    elif command == "flashcards":
        from .cli import flashcards_main

        flashcards_main()
    elif command == "collections":
        from .cli import collections_main

        collections_main()
    elif command == "ingest":
        from .ingest import main as ingest_main

        ingest_main()
    elif command == "convert":
        from .convert import main as convert_main

        convert_main()
    elif command == "api":
        from .api import main as api_main

        api_main()
    elif command == "setup":
        from .setup import main as setup_main

        setup_main()
    elif command in ("-h", "--help", "help"):
        # Re-run with no args to show help
        sys.argv = [sys.argv[0]]
        main()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python -m corpus_callosum' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
