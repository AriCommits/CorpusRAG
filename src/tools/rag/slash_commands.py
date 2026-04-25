from dataclasses import dataclass
from typing import Any, Callable, Literal


@dataclass
class SlashCommand:
    name: str
    args: list[str]
    raw: str


@dataclass
class SlashCommandResult:
    type: Literal["text", "screen", "toast", "error", "stream"]
    content: str | None = None
    screen: Any | None = (
        None  # text.Screen is tricky to import without context, we can type hint later or import Any
    )
    toast_message: str | None = None


_registry: dict[str, dict] = {}


def slash_command(name: str, description: str):
    def decorator(fn: Callable) -> Callable:
        _registry[name] = {"fn": fn, "description": description}
        return fn

    return decorator


class SlashCommandRouter:
    """Intercept and route slash commands before LLM dispatch."""

    def is_slash_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def parse(self, text: str) -> SlashCommand:
        parts = text.strip().lstrip("/").split()
        if not parts:
            return SlashCommand(name="", args=[], raw=text)
        return SlashCommand(name=parts[0], args=parts[1:], raw=text)

    def dispatch(self, command: SlashCommand) -> SlashCommandResult:
        if not command.name:
            return SlashCommandResult(
                type="error",
                content="Empty command.\nType /help to see available commands.",
            )

        handler_info = _registry.get(command.name)
        if handler_info is None:
            return SlashCommandResult(
                type="error",
                content=f"Unknown command: /{command.name}\nType /help to see available commands.",
            )

        handler = handler_info["fn"]
        return handler(command.args)


@slash_command("help", "List all registered slash commands with descriptions")
def handle_help(args: list[str]) -> SlashCommandResult:
    lines = ["Available commands:"]
    for cmd_name, info in sorted(_registry.items()):
        lines.append(f"  /{cmd_name.ljust(15)} {info['description']}")
    return SlashCommandResult(type="text", content="\n".join(lines))


@slash_command("clear", "Clear chat history for current session")
def handle_clear(args: list[str]) -> SlashCommandResult:
    return SlashCommandResult(
        type="toast", toast_message="Chat history cleared"
    )  # Implementation of clearing needs to happen in TUI handler if needed or we pass clear action


@slash_command("ask", "Explicit RAG query (same as typing without /)")
def handle_ask(args: list[str]) -> SlashCommandResult:
    if not args:
        return SlashCommandResult(
            type="error",
            content="Please provide a question. Example: /ask What is RAG?",
        )
    return SlashCommandResult(type="stream", content=" ".join(args))


@slash_command("sync", "Synchronize current collection with source directory")
def handle_sync(args: list[str]) -> SlashCommandResult:
    if not args:
        return SlashCommandResult(type="toast", toast_message="sync:full")
    if args[0] == "status":
        return SlashCommandResult(type="toast", toast_message="sync:status")
    if args[0] == "--dry-run":
        return SlashCommandResult(type="toast", toast_message="sync:dry-run")
    return SlashCommandResult(
        type="error", content="Usage: /sync, /sync status, or /sync --dry-run"
    )


@slash_command("export", "Export data (anki, markdown, json)")
def handle_export(args: list[str]) -> SlashCommandResult:
    if not args:
        return SlashCommandResult(
            type="error", content="Usage: /export <format> (anki, markdown, json)"
        )
    fmt = args[0].lower()
    if fmt in ["anki", "markdown", "json", "csv"]:
        return SlashCommandResult(type="toast", toast_message=f"export:{fmt}")
    return SlashCommandResult(type="error", content=f"Unknown export format: {fmt}")


@slash_command("strategy", "View or change the RAG retrieval strategy")
def handle_strategy(args: list[str]) -> SlashCommandResult:
    """Handle /strategy slash command.

    Usage:
      /strategy               - Show current strategy
      /strategy hybrid        - Switch to hybrid (vector + BM25 + RRF + reranker)
      /strategy semantic      - Switch to semantic (vector only)
      /strategy keyword       - Switch to keyword (BM25 only)
    """
    valid_strategies = ["hybrid", "semantic", "keyword"]

    if not args:
        # Show current strategy - implementation will be in TUI handler
        return SlashCommandResult(
            type="text",
            content=(
                "Available strategies: hybrid, semantic, keyword\nUse /strategy <name> to switch."
            ),
        )

    strategy_name = args[0].lower()
    if strategy_name not in valid_strategies:
        return SlashCommandResult(
            type="error",
            content=f"Unknown strategy: {strategy_name}\nAvailable: {', '.join(valid_strategies)}",
        )

    return SlashCommandResult(type="toast", toast_message=f"strategy:{strategy_name}")


@slash_command("filter", "Set tag-based filters for subsequent queries")
def handle_filter(args: list[str]) -> SlashCommandResult:
    """Handle /filter slash command.

    Usage:
      /filter                 - Show current filters
      /filter clear           - Clear all filters
      /filter <tag>           - Filter by tag prefix (e.g., /filter Skill)
      /filter <tag>/<subtag>  - Filter by hierarchical tag (e.g., /filter Skill/ML)
    """
    if not args:
        # Show current filters - implementation will be in TUI handler
        return SlashCommandResult(
            type="text",
            content="No active filters.\nUse /filter <tag> to filter by tag prefix.\nUse /filter clear to reset.",
        )

    if args[0].lower() == "clear":
        return SlashCommandResult(type="toast", toast_message="filter:clear")

    # Filter value - validate it
    filter_value = " ".join(args)
    # Basic validation: only allow alphanumeric, slashes, underscores
    if not all(c.isalnum() or c in "/_-" for c in filter_value):
        return SlashCommandResult(
            type="error",
            content=f"Invalid filter value: {filter_value}\nOnly alphanumeric, slashes, hyphens, and underscores allowed.",
        )

    return SlashCommandResult(type="toast", toast_message=f"filter:{filter_value}")


@slash_command("context", "Manage message inclusion in context")
def handle_context(args: list[str]) -> SlashCommandResult:
    """Handle /context slash command.

    Usage:
      /context              - Show context usage stats
      /context show         - Toggle context sidebar visibility
      /context clear        - Exclude all messages except last exchange
      /context include all  - Include all messages in context
    """
    if not args:
        return SlashCommandResult(
            type="text",
            content="Context management commands:\n  /context show - Toggle sidebar\n  /context clear - Exclude all but last exchange\n  /context include all - Include all messages",
        )

    cmd = args[0].lower()
    if cmd == "show":
        return SlashCommandResult(type="toast", toast_message="context:show")
    elif cmd == "clear":
        return SlashCommandResult(type="toast", toast_message="context:clear")
    elif cmd == "include" and len(args) > 1 and args[1].lower() == "all":
        return SlashCommandResult(type="toast", toast_message="context:include_all")
    else:
        return SlashCommandResult(
            type="error",
            content="Unknown context command.\nUse: /context show, /context clear, or /context include all",
        )
