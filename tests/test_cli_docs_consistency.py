"""CLI ↔ documentation consistency tests.

These tests express universal invariants over the *live* Click command tree and
the checked-in documentation. They enumerate the real command set and every
documented example (no random input), so they are written as plain enumerated
assertions rather than randomized property tests.
"""

import re
import shlex
from pathlib import Path

import click

from cli import corpus

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Command-tree helpers
# ---------------------------------------------------------------------------
def _ctx() -> click.Context:
    return click.Context(corpus)


def _top_level_commands() -> set[str]:
    """Top-level command names from the live root group."""
    return set(corpus.list_commands(_ctx()))


def build_command_tree() -> dict:
    """Construct the full command tree from the live root ``corpus`` group.

    Enumerates top-level commands via ``corpus.list_commands`` and resolves each
    subcommand via ``get_command`` (triggering the LazyGroup import). Recurses
    into any resolved command that is itself a ``click.Group``.
    """

    def _walk(group: click.Group) -> dict:
        ctx = _ctx()
        tree: dict = {}
        for name in group.list_commands(ctx):
            cmd = group.get_command(ctx, name)
            if isinstance(cmd, click.Group):
                tree[name] = _walk(cmd)
            else:
                tree[name] = None
        return tree

    return _walk(corpus)


# ---------------------------------------------------------------------------
# cli.txt parsing
# ---------------------------------------------------------------------------
def _read_text_any(path: Path) -> str:
    """Read a text file, tolerating UTF-8/UTF-8-BOM/UTF-16 encodings."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def _parse_cli_txt_top_level() -> set[str]:
    """Parse top-level command names from the ``Commands:`` section of cli.txt."""
    text = _read_text_any(ROOT / "cli.txt")
    commands: set[str] = set()
    in_section = False
    for line in text.splitlines():
        if line.strip() == "Commands:":
            in_section = True
            continue
        if not in_section:
            continue
        if not line.strip():
            # blank line terminates the Commands section
            break
        # Command rows are indented exactly two spaces; wrapped description
        # continuation lines are indented further and are ignored.
        match = re.match(r"^ {2}(\S+)", line)
        if match:
            commands.add(match.group(1))
    return commands


# ---------------------------------------------------------------------------
# Documentation example extraction
# ---------------------------------------------------------------------------
_DOC_FILES = [
    ("README.md", ROOT / "README.md"),
    ("src/CLI.md", ROOT / "src" / "CLI.md"),
    ("docs/architecture.md", ROOT / "docs" / "architecture.md"),
    ("docs/tools-usage.md", ROOT / "docs" / "tools-usage.md"),
    ("docs/mcp-integration.md", ROOT / "docs" / "mcp-integration.md"),
    ("docs/docker-deployment.md", ROOT / "docs" / "docker-deployment.md"),
    ("docs/troubleshooting.md", ROOT / "docs" / "troubleshooting.md"),
    ("docs/configuration.md", ROOT / "docs" / "configuration.md"),
]


def _extract_corpus_examples(path: Path) -> list[str]:
    """Extract candidate ``corpus ...`` invocations from fenced code blocks.

    Scans ```bash / ```text fenced blocks for lines beginning with ``corpus ``
    (a space after ``corpus``). Excludes hyphenated entrypoints like
    ``corpus-mcp-server`` (no space) and bare / option-only invocations such as
    ``corpus``, ``corpus --help``, ``corpus --version``.
    """
    text = path.read_text(encoding="utf-8")
    examples: list[str] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_block:
                lang = stripped[3:].strip().lower()
                in_block = lang in ("bash", "text")
            else:
                in_block = False
            continue
        if not in_block:
            continue
        content = line.strip()
        if not content.startswith("corpus "):
            continue
        try:
            tokens = shlex.split(content, comments=True)
        except ValueError:
            tokens = content.split()
        if not tokens or tokens[0] != "corpus":
            continue
        rest = tokens[1:]
        # Exclude bare / option-only invocations (e.g. `corpus --help`).
        if not rest or rest[0].startswith("-"):
            continue
        examples.append(content)
    return examples


def _resolves(command_line: str) -> bool:
    """Return True if a documented ``corpus`` example resolves to a real command.

    Tokenizes the line, drops the leading ``corpus``, then walks tokens as a
    command path: descend while a token does not start with ``-`` and is a
    subcommand of the current group. Stop at the first token that starts with
    ``-`` or is not a subcommand (treated as an argument/option). Resolves iff
    the first path token matched a real subcommand (every consumed token exists
    by construction).
    """
    try:
        tokens = shlex.split(command_line, comments=True)
    except ValueError:
        tokens = command_line.split()
    rest = tokens[1:]  # drop leading "corpus"

    node: click.Command = corpus
    matched_first = False
    for index, token in enumerate(rest):
        if token.startswith("-"):
            break
        if not isinstance(node, click.Group):
            break
        sub = node.get_command(_ctx(), token)
        if sub is None:
            break
        node = sub
        if index == 0:
            matched_first = True
    return matched_first


# ---------------------------------------------------------------------------
# Property 1
# ---------------------------------------------------------------------------
def test_cli_txt_matches_live_command_tree() -> None:
    # Feature: project-hardening, Property 1: cli.txt matches the live command tree exactly
    documented = _parse_cli_txt_top_level()
    live = _top_level_commands()

    missing = live - documented  # live commands not documented in cli.txt
    extra = documented - live  # cli.txt entries with no live command

    assert documented == live, (
        "cli.txt top-level commands do not match the live command tree.\n"
        f"  Missing from cli.txt (present live): {sorted(missing)}\n"
        f"  Extra in cli.txt (not a live command): {sorted(extra)}\n"
        f"  Live: {sorted(live)}\n"
        f"  cli.txt: {sorted(documented)}"
    )


# ---------------------------------------------------------------------------
# Property 2
# ---------------------------------------------------------------------------
def test_documented_command_examples_resolve() -> None:
    # Feature: project-hardening, Property 2: every documented command example resolves to a real command
    failures: list[tuple[str, str]] = []
    for source, path in _DOC_FILES:
        for command_line in _extract_corpus_examples(path):
            if not _resolves(command_line):
                failures.append((source, command_line))

    if failures:
        detail = "\n".join(f"  [{src}] {cmd}" for src, cmd in failures)
        raise AssertionError(
            "Documented command examples that do not resolve to a real command:\n" + detail
        )


_STALE_DOC_FILES = [
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "tools-usage.md",
    ROOT / "docs" / "mcp-integration.md",
    ROOT / "docs" / "docker-deployment.md",
    ROOT / "docs" / "troubleshooting.md",
    ROOT / "docs" / "configuration.md",
]

_STALE_PATTERNS = (
    "CorpusCallosum",
    "corpus-rag ",
    "corpus-flashcards",
    "corpus-db ",
    "corpus-orchestrate",
    "schema.py",
    "StudySessionOrchestrator",
    "KnowledgeBaseOrchestrator",
    "lecture_processing_prompt",
    "automatically available via MCP",
)


def test_plan21_docs_drop_stale_product_and_cli_names() -> None:
    """User-facing docs must not describe the pre-CorpusRAG / standalone CLI."""
    failures: list[str] = []
    for path in _STALE_DOC_FILES:
        text = path.read_text(encoding="utf-8")
        for pattern in _STALE_PATTERNS:
            if pattern in text:
                failures.append(f"{path.relative_to(ROOT)}: {pattern!r}")
    assert not failures, "Stale documentation strings still present:\n  " + "\n  ".join(failures)
