"""CLI interface for video tool."""

from pathlib import Path

import click

from corpus_callosum.config.loader import load_config

from .augment import TranscriptAugmenter
from .clean import TranscriptCleaner
from .config import VideoConfig
from .transcribe import VideoTranscriber


@click.group()
def video():
    """Video transcription and processing tool."""
    pass


@video.command()
@click.argument("input_folder", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--course", "-c", default=None, help="Course identifier (e.g., BIOL101)")
@click.option("--lecture", "-l", default=None, type=int, help="Lecture number")
def transcribe(input_folder: str, output: str, config: str, course: str, lecture: int):
    """Transcribe video files to text."""
    # Load config
    config_data = load_config(config)
    cfg = VideoConfig.from_dict(config_data)
    
    # Initialize transcriber
    transcriber = VideoTranscriber(cfg)
    
    # Transcribe
    click.echo(f"Transcribing videos from {input_folder}...")
    transcripts = transcriber.transcribe_folder(Path(input_folder), course, lecture)
    
    # Combine transcripts
    combined = transcriber.combine_transcripts(transcripts, course, lecture)
    
    # Write or print
    if output:
        output_path = Path(output)
    elif course and lecture:
        output_path = Path(cfg.paths.output) / f"{course}_Lecture{lecture:02d}_transcript.md"
    else:
        output_path = Path(cfg.paths.output) / "transcript.md"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined)
    
    click.echo(f"✓ Transcribed {len(transcripts)} videos to {output_path}")


@video.command()
@click.argument("transcript_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def clean(transcript_file: str, output: str, config: str):
    """Clean a raw transcript using LLM."""
    # Load config
    config_data = load_config(config)
    cfg = VideoConfig.from_dict(config_data)
    
    # Initialize cleaner
    cleaner = TranscriptCleaner(cfg)
    
    # Clean transcript
    click.echo(f"Cleaning transcript {transcript_file}...")
    output_path = cleaner.clean_file(Path(transcript_file), Path(output) if output else None)
    
    click.echo(f"✓ Cleaned transcript written to {output_path}")


@video.command()
@click.argument("transcript_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--auto", is_flag=True, help="Skip manual editing")
def augment(transcript_file: str, output: str, config: str, auto: bool):
    """Augment transcript with manual annotations."""
    # Load config
    config_data = load_config(config)
    cfg = VideoConfig.from_dict(config_data)
    
    # Initialize augmenter
    augmenter = TranscriptAugmenter(cfg)
    
    # Augment transcript
    click.echo(f"Augmenting transcript {transcript_file}...")
    output_path = augmenter.augment(
        Path(transcript_file),
        Path(output) if output else None,
        auto_save=auto,
    )
    
    click.echo(f"✓ Final transcript written to {output_path}")


@video.command()
@click.argument("input_folder", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Final output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--course", "-c", default=None, help="Course identifier")
@click.option("--lecture", "-l", default=None, type=int, help="Lecture number")
@click.option("--skip-clean", is_flag=True, help="Skip cleaning step")
@click.option("--skip-augment", is_flag=True, help="Skip augmentation step")
def pipeline(
    input_folder: str,
    output: str,
    config: str,
    course: str,
    lecture: int,
    skip_clean: bool,
    skip_augment: bool,
):
    """Run complete video processing pipeline."""
    # Load config
    config_data = load_config(config)
    cfg = VideoConfig.from_dict(config_data)
    
    # Create scratch directory
    scratch = Path(cfg.paths.scratch) / f"{course}_Lecture{lecture:02d}" if course and lecture else Path(cfg.paths.scratch) / "video"
    scratch.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Transcribe
    click.echo("Step 1: Transcribing...")
    transcriber = VideoTranscriber(cfg)
    transcripts = transcriber.transcribe_folder(Path(input_folder), course, lecture)
    combined = transcriber.combine_transcripts(transcripts, course, lecture)
    
    raw_transcript = scratch / "raw_transcript.md"
    raw_transcript.write_text(combined)
    click.echo(f"✓ Raw transcript: {raw_transcript}")
    
    current_file = raw_transcript
    
    # Step 2: Clean (optional)
    if not skip_clean:
        click.echo("\nStep 2: Cleaning...")
        cleaner = TranscriptCleaner(cfg)
        current_file = cleaner.clean_file(current_file)
        click.echo(f"✓ Cleaned transcript: {current_file}")
    
    # Step 3: Augment (optional)
    if not skip_augment:
        click.echo("\nStep 3: Augmenting...")
        augmenter = TranscriptAugmenter(cfg)
        
        if output:
            final_path = Path(output)
        elif course and lecture:
            final_path = Path(cfg.paths.output) / f"{course}_Lecture{lecture:02d}_final.md"
        else:
            final_path = Path(cfg.paths.output) / "final_transcript.md"
        
        current_file = augmenter.augment(current_file, final_path, auto_save=False)
    
    click.echo(f"\n✓ Pipeline complete! Final output: {current_file}")


def main():
    """Entry point for corpus-video CLI."""
    video()


if __name__ == "__main__":
    main()
