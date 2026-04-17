"""Developer helper commands — cross-platform replacement for shell scripts."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

ROOT = Path(__file__).parent.parent  # repo root


@click.group()
def dev() -> None:
    """Developer utilities (setup, test, lint, build, clean, completion)."""


@dev.command()
def setup() -> None:
    """Install package in editable mode and verify environment."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        cwd=ROOT,
        check=True,
    )
    click.echo("Environment ready.")


@dev.command()
@click.option("--cov", is_flag=True, help="Enable coverage report")
def test(cov: bool) -> None:
    """Run the test suite cross-platform."""
    cmd = [sys.executable, "-m", "pytest"]
    if cov:
        cmd += ["--cov=src", "--cov-report=term-missing"]
    subprocess.run(cmd, cwd=ROOT, check=True)


@dev.command()
def lint() -> None:
    """Run ruff check + mypy."""
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        cwd=ROOT,
        check=True,
    )


@dev.command()
def fmt() -> None:
    """Run ruff format."""
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", "src", "tests"],
        cwd=ROOT,
        check=True,
    )


@dev.command()
def build() -> None:
    """Build the distribution package."""
    subprocess.run([sys.executable, "-m", "build"], cwd=ROOT, check=True)


@dev.command()
def clean() -> None:
    """Remove build artifacts and __pycache__ trees cross-platform."""
    patterns = ["build", "dist", "*.egg-info", "**/__pycache__", "**/*.pyc"]
    removed = 0
    for pattern in patterns:
        for p in ROOT.glob(pattern):
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed += 1
    click.echo(f"Cleaned {removed} artifact(s).")


@dev.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish", "powershell"]))
def completion(shell: str) -> None:
    """Print shell completion setup instructions for SHELL."""
    env_var = "_CORPUS_COMPLETE"
    snippets = {
        "bash": f'eval "$({env_var}=bash_source corpus)"',
        "zsh": f'eval "$({env_var}=zsh_source corpus)"',
        "fish": f"{env_var}=fish_source corpus | source",
        "powershell": (
            "& corpus --show-completion powershell | Out-String | Invoke-Expression"
        ),
    }
    click.echo(f"Add this to your shell profile:\n\n    {snippets[shell]}")
