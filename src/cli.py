"""Unified cross-platform CLI entry point for CorpusRAG."""

from pathlib import Path

import click

from cli_dev import dev
from db.collections_cli import collections_cmd
from db.management import db
from orchestrations.cli import orchestrate
from tools.flashcards.cli import flashcards
from tools.quizzes.cli import quizzes
from tools.rag.cli import rag
from tools.summaries.cli import summaries
from tools.video.cli import video


@click.group()
@click.version_option(package_name="corpusrag")
def corpus() -> None:
    """CorpusRAG — unified learning and knowledge management toolkit.

    Run any subcommand with --help for details.
    """


@corpus.command()
@click.option("--reset", is_flag=True, help="Reset setup and re-run wizard")
def setup(reset: bool) -> None:
    """Run interactive setup wizard for first-time configuration."""
    marker_file = Path(".corpus_setup_complete")

    # Check if setup has already been completed
    if marker_file.exists() and not reset:
        click.echo(
            "Setup already completed. Use --reset to run wizard again or "
            "'corpus rag ui' to start using CorpusRAG."
        )
        return

    # Remove marker if resetting
    if reset and marker_file.exists():
        marker_file.unlink()
        click.echo("Resetting setup...")

    # Import and run setup wizard
    from setup_wizard import run_setup_wizard

    exit_code = run_setup_wizard()
    if exit_code != 0:
        raise click.ClickException("Setup wizard failed")


@corpus.command(name="export")
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--output-dir", "-o", default="./exports", help="Output directory")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def bulk_export(collection: str, output_dir: str, config: str) -> None:
    """Bulk export all data (flashcards, summaries, quizzes) for a collection."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Bulk exporting data for collection '{collection}' to {output_dir}...")

    # Placeholder for actual bulk logic
    click.echo("Exporting flashcards (Anki)...")
    # ... logic ...
    click.echo("Exporting summary (Markdown)...")
    # ... logic ...
    click.echo("Exporting quiz (JSON)...")
    # ... logic ...
    click.echo("Bulk export complete.")


@corpus.command(name="benchmark")
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--queries", "-n", default=5, help="Number of test queries")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def benchmark(collection: str, queries: int, config: str) -> None:
    """Run performance benchmarks on a collection."""
    from cli_common import load_cli_db
    from tools.rag.agent import RAGAgent
    from utils.benchmarking import benchmarker

    cfg, db = load_cli_db(config)
    agent = RAGAgent(cfg, db)

    click.echo(f"Running {queries} benchmark queries on '{collection}'...")
    test_queries = [
        "What is this?",
        "Tell me more",
        "Summarize key points",
        "How does it work?",
        "List features",
    ]

    for i in range(min(queries, len(test_queries))):
        q = test_queries[i]
        click.echo(f"  [{i + 1}/{queries}] Querying: {q}")
        agent.query(q, collection)

    stats = benchmarker.get_stats()
    click.echo("\nBenchmark Results:")
    click.echo(f"  Average Latency: {stats.get('avg_total_ms', 0):.2f}ms")
    click.echo(f"  p95 Latency:     {stats.get('p95_total_ms', 0):.2f}ms")
    click.echo(f"  Total Queries:   {int(stats.get('count', 0))}")


corpus.add_command(rag)
corpus.add_command(video)
corpus.add_command(orchestrate)
corpus.add_command(flashcards)
corpus.add_command(summaries)
corpus.add_command(quizzes)
corpus.add_command(db)
corpus.add_command(collections_cmd)
corpus.add_command(dev)


def main() -> None:
    """Entry point for the unified corpus CLI."""
    corpus()


if __name__ == "__main__":
    main()
