---
title: Cross-Platform Python CLI Interface Plan
date: 2026-04-13
status: draft
---

# Plan: Unified Cross-Platform Python CLI for Corpus Callosum

## Context

The project already uses `click` and `typer` for individual tool CLIs (`corpus-rag`, `corpus-flashcards`, `corpus-video`, etc.), but there is no unified top-level entry point and no cross-platform scripting strategy. This plan replaces any shell-script-based workflows with a consistent Python-only CLI that behaves identically on PowerShell, bash, and zsh.

---

## Goals

- [ ] Single `corpus` top-level command that wraps all subgroups
- [ ] Python-only developer scripts (no `.sh` / `.ps1` duality)
- [ ] Cross-platform `pathlib.Path` usage everywhere (no hardcoded `/` or `\`)
- [ ] Rich terminal output (colors, tables, progress bars) that degrades gracefully on dumb terminals
- [ ] Shell completion for bash, zsh, fish, and PowerShell via Click
- [ ] Interactive REPL/wizard mode for new users

---

## Architecture

```
corpus/               ← unified top-level group
├── rag               ← tools.rag.cli (existing)
├── flashcards        ← tools.flashcards.cli (existing)
├── summaries         ← tools.summaries.cli (existing)
├── quizzes           ← tools.quizzes.cli (existing)
├── video             ← tools.video.cli (existing)
├── orchestrate       ← orchestrations.cli (existing)
├── db                ← db.management (existing)
├── secrets           ← utils.manage_secrets (existing)
├── keys              ← utils.manage_keys (existing)
└── dev               ← NEW: developer helper commands (replaces shell scripts)
    ├── setup         install + configure environment
    ├── test          run tests cross-platform
    ├── lint          run ruff + mypy
    ├── build         build package
    └── clean         remove __pycache__, .pyc, build artifacts
```

---

## Implementation Steps

### Step 1 — Create `src/cli.py` (Unified Entry Point)

```python
"""Unified cross-platform CLI entry point for Corpus Callosum."""
import click
from tools.rag.cli import rag
from tools.flashcards.cli import flashcards
from tools.summaries.cli import summaries
from tools.quizzes.cli import quizzes
from tools.video.cli import video
from orchestrations.cli import orchestrate
from db.management import db
from utils.manage_secrets import secrets
from utils.manage_keys import keys
from cli_dev import dev  # new

@click.group()
@click.version_option()
def corpus():
    """Corpus Callosum — unified learning and knowledge management toolkit."""

corpus.add_command(rag)
corpus.add_command(flashcards)
corpus.add_command(summaries)
corpus.add_command(quizzes)
corpus.add_command(video)
corpus.add_command(orchestrate)
corpus.add_command(db)
corpus.add_command(secrets)
corpus.add_command(keys)
corpus.add_command(dev)

def main():
    corpus()
```

### Step 2 — Register `corpus` in `pyproject.toml`

```toml
[project.scripts]
corpus = "cli:main"          # ← NEW unified entry point
# keep individual corpus-* entries for backwards compat
```

### Step 3 — Create `src/cli_dev.py` (Replaces All Shell Scripts)

This module replaces any `.sh` / `.ps1` scripts with Python equivalents using `subprocess` and `pathlib`.

```python
"""Developer helper commands — cross-platform replacement for shell scripts."""
import subprocess, sys
from pathlib import Path
import click

ROOT = Path(__file__).parent.parent  # repo root

@click.group()
def dev():
    """Developer utilities (setup, test, lint, build, clean)."""

@dev.command()
def setup():
    """Install package in editable mode and verify environment."""
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
                   cwd=ROOT, check=True)
    click.echo("Environment ready.")

@dev.command()
@click.option("--cov", is_flag=True, help="Enable coverage report")
def test(cov: bool):
    """Run the test suite cross-platform."""
    cmd = [sys.executable, "-m", "pytest"]
    if cov:
        cmd += ["--cov=src", "--cov-report=term-missing"]
    subprocess.run(cmd, cwd=ROOT, check=True)

@dev.command()
def lint():
    """Run ruff + mypy."""
    subprocess.run([sys.executable, "-m", "ruff", "check", "src", "tests"],
                   cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "mypy", "src"],
                   cwd=ROOT, check=True)

@dev.command()
def build():
    """Build the distribution package."""
    subprocess.run([sys.executable, "-m", "build"], cwd=ROOT, check=True)

@dev.command()
def clean():
    """Remove build artifacts and __pycache__ trees cross-platform."""
    import shutil
    patterns = ["build", "dist", "*.egg-info", "**/__pycache__", "**/*.pyc"]
    for pattern in patterns:
        for p in ROOT.glob(pattern):
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    click.echo("Cleaned.")
```

### Step 4 — Shell Completion Setup (Cross-Platform)

Add completion instructions to `README.md` and a `corpus dev completion` subcommand:

```python
@dev.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish", "powershell"]))
def completion(shell: str):
    """Print shell completion setup instructions."""
    env_var = "_CORPUS_COMPLETE"
    shells = {
        "bash":        f'eval "$({env_var}=bash_source corpus)"',
        "zsh":         f'eval "$({env_var}=zsh_source corpus)"',
        "fish":        f'{env_var}=fish_source corpus | source',
        "powershell":  f'& corpus --show-completion powershell | Out-String | Invoke-Expression',
    }
    click.echo(f"Add this to your shell profile:\n\n    {shells[shell]}")
```

### Step 5 — Cross-Platform Path Handling Audit

Grep every source file for string concatenation with `"/"` or `"\\"` in path contexts and replace with `pathlib.Path` operations. Key files to audit:

- `src/tools/video/transcribe.py`
- `src/tools/rag/ingest.py`
- `src/config/loader.py`
- `src/db/chroma.py`

### Step 6 — Rich Output Integration

Wrap `click.echo` calls in `src/orchestrations/cli.py` and tool CLIs with `rich.console.Console` for colored tables and progress bars. Use `console.print()` with `Rich` markup. Guard with `TERM=dumb` / `NO_COLOR` env var detection (Rich handles this automatically).

---

## Testing Plan

- [ ] `pytest tests/unit/test_cli.py` — unit tests for unified entry point
- [ ] Manual smoke test on Windows PowerShell: `corpus --help`, `corpus dev test`
- [ ] Manual smoke test on macOS zsh: `corpus --help`, `corpus dev lint`
- [ ] Verify no hardcoded path separators remain after audit

---

## Non-Goals

- No GUI / TUI (curses) — CLI only
- No Docker or CI pipeline changes in this plan
- No breaking changes to existing `corpus-*` entry points

---

## Files to Create / Modify

| File | Action |
|---|---|
| `src/cli.py` | CREATE — unified group |
| `src/cli_dev.py` | CREATE — dev helpers |
| `pyproject.toml` | MODIFY — add `corpus` entry point |
| `src/orchestrations/cli.py` | MODIFY — expose `orchestrate` group directly |
| `src/tools/*/cli.py` | MODIFY — expose Click groups at module level |
| `src/config/loader.py` | MODIFY — pathlib audit |
| `src/tools/rag/ingest.py` | MODIFY — pathlib audit |
