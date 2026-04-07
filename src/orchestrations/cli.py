"""CLI for orchestrations."""

from pathlib import Path

import click

from corpus_callosum.config.loader import load_config
from corpus_callosum.db.chroma import ChromaDBBackend
from corpus_callosum.orchestrations import (
    KnowledgeBaseOrchestrator,
    LecturePipelineOrchestrator,
    StudySessionOrchestrator,
)


@click.group()
def orchestrate():
    """Orchestration workflows for Corpus Callosum."""
    pass


@orchestrate.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--topic", "-t", default=None, help="Specific topic")
@click.option("--flashcards", "-f", default=15, type=int, help="Number of flashcards")
@click.option("--quiz", "-q", default=10, type=int, help="Number of quiz questions")
@click.option("--length", "-l", default="medium", type=click.Choice(["short", "medium", "long"]), help="Summary length")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-cfg", default="configs/base.yaml", help="Config file")
def study_session(collection: str, topic: str, flashcards: int, quiz: int, length: str, output: str, config: str):
    """Create a comprehensive study session."""
    # Load config
    config_data = load_config(config)
    db = ChromaDBBackend(config_data.database)
    
    # Create orchestrator
    orchestrator = StudySessionOrchestrator(config_data, db)
    
    # Generate study session
    click.echo(f"Creating study session for collection '{collection}'...")
    session = orchestrator.create_session(
        collection=collection,
        topic=topic,
        flashcard_count=flashcards,
        quiz_count=quiz,
        summary_length=length,
    )
    
    # Format and output
    formatted = orchestrator.format_session(session)
    
    if output:
        Path(output).write_text(formatted)
        click.echo(f"✓ Study session written to {output}")
    else:
        click.echo("\n" + formatted)


@orchestrate.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--course", "-c", required=True, help="Course identifier (e.g., BIOL101)")
@click.option("--lecture", "-l", required=True, type=int, help="Lecture number")
@click.option("--skip-clean", is_flag=True, help="Skip transcript cleaning")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-cfg", default="configs/base.yaml", help="Config file")
def lecture_pipeline(video_path: str, course: str, lecture: int, skip_clean: bool, output: str, config: str):
    """Process a lecture video into complete study materials."""
    # Load config
    config_data = load_config(config)
    db = ChromaDBBackend(config_data.database)
    
    # Create orchestrator
    orchestrator = LecturePipelineOrchestrator(config_data, db)
    
    # Process lecture
    click.echo(f"Processing lecture {lecture} for course {course}...")
    result = orchestrator.process_lecture(
        video_path=Path(video_path),
        course=course,
        lecture_num=lecture,
        skip_clean=skip_clean,
    )
    
    # Format and output
    formatted = orchestrator.format_lecture_materials(result)
    
    if output:
        Path(output).write_text(formatted)
        click.echo(f"✓ Lecture materials written to {output}")
    else:
        click.echo("\n" + formatted)


@orchestrate.command()
@click.argument("source_path", type=click.Path(exists=True))
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option("--config", "-cfg", default="configs/base.yaml", help="Config file")
def build_kb(source_path: str, collection: str, config: str):
    """Build a knowledge base from documents."""
    # Load config
    config_data = load_config(config)
    db = ChromaDBBackend(config_data.database)
    
    # Create orchestrator
    orchestrator = KnowledgeBaseOrchestrator(config_data, db)
    
    # Build knowledge base
    click.echo(f"Building knowledge base '{collection}' from {source_path}...")
    result = orchestrator.build_knowledge_base(
        source_path=Path(source_path),
        collection=collection,
    )
    
    click.echo(f"✓ Processed {result['documents_processed']} documents, created {result['chunks_created']} chunks")


@orchestrate.command()
@click.option("--collection", "-c", required=True, help="Collection name")
@click.argument("query")
@click.option("--top-k", "-k", default=5, type=int, help="Number of results")
@click.option("--no-response", is_flag=True, help="Only retrieve chunks, don't generate response")
@click.option("--config", "-cfg", default="configs/base.yaml", help="Config file")
def query_kb(collection: str, query: str, top_k: int, no_response: bool, config: str):
    """Query a knowledge base."""
    # Load config
    config_data = load_config(config)
    db = ChromaDBBackend(config_data.database)
    
    # Create orchestrator
    orchestrator = KnowledgeBaseOrchestrator(config_data, db)
    
    # Query
    click.echo(f"Querying collection '{collection}'...")
    result = orchestrator.query_knowledge_base(
        collection=collection,
        query=query,
        top_k=top_k,
        generate_response=not no_response,
    )
    
    # Display results
    if "response" in result:
        click.echo(f"\n{result['response']}")
    else:
        click.echo(f"\nFound {len(result['chunks'])} relevant chunks:")
        for idx, chunk in enumerate(result['chunks'], 1):
            click.echo(f"\n{idx}. Score: {chunk['score']:.3f}")
            click.echo(f"   Source: {chunk['source']}")
            click.echo(f"   {chunk['text'][:200]}...")


def main():
    """Entry point for orchestrations CLI."""
    orchestrate()


if __name__ == "__main__":
    main()
