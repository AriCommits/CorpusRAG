"""Unified cross-platform CLI entry point for CorpusRAG."""

from pathlib import Path

import click

from cli_lazy import LazyGroup


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "rag": "tools.rag.cli:rag",
        "video": "tools.video.cli:video",
        "orchestrate": "orchestrations.cli:orchestrate",
        "flashcards": "tools.flashcards.cli:flashcards",
        "summaries": "tools.summaries.cli:summaries",
        "quizzes": "tools.quizzes.cli:quizzes",
        "db": "db.management:db",
        "collections": "db.collections_cli:collections_cmd",
        "dev": "cli_dev:dev",
    },
)
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

    if marker_file.exists() and not reset:
        click.echo(
            "Setup already completed. Use --reset to run wizard again or "
            "'corpus rag ui' to start using CorpusRAG."
        )
        return

    if reset and marker_file.exists():
        marker_file.unlink()
        click.echo("Resetting setup...")

    from setup_wizard import run_setup_wizard

    exit_code = run_setup_wizard()
    if exit_code != 0:
        raise click.ClickException("Setup wizard failed")


@corpus.command(name="benchmark")
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--queries", "-n", default=5, help="Number of test queries")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def benchmark(collection: str, queries: int, config: str) -> None:
    """Run performance benchmarks on a collection."""
    from cli_common import load_cli_db
    from tools.rag.agent import RAGAgent
    from utils.benchmarking import benchmarker

    cfg, db_backend = load_cli_db(config)
    agent = RAGAgent(cfg, db_backend)

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


def main() -> None:
    """Entry point for the unified corpus CLI."""
    corpus()


if __name__ == "__main__":
    main()
