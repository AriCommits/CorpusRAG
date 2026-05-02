"""CLI interface for video tool."""

from pathlib import Path

import click

from cli_common import load_cli_config

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
@click.option("--clean", is_flag=True, help="Run LLM cleaning after transcription")
def transcribe(input_folder: str, output: str, config: str, course: str, lecture: int, clean: bool):
    """Transcribe video files to text."""
    cfg = load_cli_config(config, VideoConfig)

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
        output_path = cfg.paths.output_dir / f"{course}_Lecture{lecture:02d}_transcript.md"
    else:
        output_path = cfg.paths.output_dir / "transcript.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined)

    click.echo(f"✓ Transcribed {len(transcripts)} videos to {output_path}")

    if clean:
        click.echo("Cleaning transcript...")
        cleaner = TranscriptCleaner(cfg)
        cleaned_path = cleaner.clean_file(output_path)
        click.echo(f"✓ Cleaned transcript written to {cleaned_path}")


@video.command()
@click.argument("transcript_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def clean(transcript_file: str, output: str, config: str):
    """Clean a raw transcript using LLM."""
    cfg = load_cli_config(config, VideoConfig)

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
    cfg = load_cli_config(config, VideoConfig)

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
    cfg = load_cli_config(config, VideoConfig)

    # Create scratch directory
    scratch = (
        cfg.paths.scratch_dir / f"{course}_Lecture{lecture:02d}"
        if course and lecture
        else cfg.paths.scratch_dir / "video"
    )
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
            final_path = cfg.paths.output_dir / f"{course}_Lecture{lecture:02d}_final.md"
        else:
            final_path = cfg.paths.output_dir / "final_transcript.md"

        current_file = augmenter.augment(current_file, final_path, auto_save=False)

    click.echo(f"\n✓ Pipeline complete! Final output: {current_file}")



@video.command("ingest")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("--collection", "-c", required=True, help="Target collection")
@click.option("--threshold", default=None, type=float, help="Scene detection sensitivity (0.0-1.0)")
@click.option("--model", default=None, help="Ollama vision model for OCR")
@click.option("--no-latex", is_flag=True, help="Disable pix2tex math fallback")
@click.option("--context-window", default=None, type=int, help="Adjacent frames per chunk")
@click.option("--keep-frames", is_flag=True, help="Keep extracted frames after ingest")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def ingest_cmd(video_path, collection, threshold, model, no_latex, context_window, keep_frames, config):
    """Ingest a video file using visual OCR pipeline."""
    from tools.video.ingest import ingest_video

    cfg = load_cli_config(config, VideoConfig)

    click.echo(f"Ingesting {video_path.name} via visual OCR...")

    with click.progressbar(length=100, label="Processing") as bar:
        last_pct = [0]
        def progress_cb(pct, step):
            delta = pct - last_pct[0]
            if delta > 0:
                bar.update(delta)
                last_pct[0] = pct

        result = ingest_video(
            video_path, cfg,
            output_dir=cfg.paths.output_dir / "video_ocr",
            progress_cb=progress_cb,
            scene_threshold=threshold,
            vision_model=model,
            use_latex_fallback=not no_latex if no_latex else None,
            context_window=context_window,
            cleanup_frames=not keep_frames,
        )

    click.echo(f"\n\u2713 Ingest complete")
    click.echo(f"  Frames extracted:  {result.frames_extracted}")
    click.echo(f"  Frames skipped:    {result.frames_skipped}")
    click.echo(f"  Chunks stored:     {result.chunks_after_dedup}")
    click.echo(f"  Duration:          {result.duration_sec:.0f}s")
    if result.output_path:
        click.echo(f"  Output:            {result.output_path}")


@video.command("ingest-url")
@click.argument("url")
@click.option("--collection", "-c", required=True, help="Target collection")
@click.option("--threshold", default=None, type=float, help="Scene detection sensitivity")
@click.option("--model", default=None, help="Ollama vision model for OCR")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def ingest_url_cmd(url, collection, threshold, model, config):
    """Download a video from URL and ingest via visual OCR."""
    from tools.video.download import download_video
    from tools.video.ingest import ingest_video

    cfg = load_cli_config(config, VideoConfig)
    dl_dir = cfg.paths.scratch_dir / "downloads"

    click.echo(f"Downloading {url}...")
    dl_result = download_video(url, dl_dir)
    click.echo(f"\u2713 Downloaded: {dl_result.title} ({dl_result.duration_sec:.0f}s)")

    click.echo(f"Ingesting via visual OCR...")
    with click.progressbar(length=100, label="Processing") as bar:
        last_pct = [0]
        def progress_cb(pct, step):
            delta = pct - last_pct[0]
            if delta > 0:
                bar.update(delta)
                last_pct[0] = pct

        result = ingest_video(
            dl_result.local_path, cfg,
            output_dir=cfg.paths.output_dir / "video_ocr",
            progress_cb=progress_cb,
            scene_threshold=threshold,
            vision_model=model,
        )

    click.echo(f"\n\u2713 Ingest complete")
    click.echo(f"  Frames extracted:  {result.frames_extracted}")
    click.echo(f"  Chunks stored:     {result.chunks_after_dedup}")
    if result.output_path:
        click.echo(f"  Output:            {result.output_path}")


@video.command("jobs")
def list_jobs_cmd():
    """List active video processing jobs."""
    from tools.video.jobs import get_job_manager

    mgr = get_job_manager()
    jobs = mgr.list_jobs()
    if not jobs:
        click.echo("No active jobs.")
        return
    for j in jobs:
        click.echo(f"  {j.job_id}  {j.status.value:8s}  {j.progress_pct:3d}%  {j.current_step}")


@video.command("status")
@click.argument("job_id")
def job_status_cmd(job_id):
    """Check status of a video processing job."""
    from tools.video.jobs import get_job_manager

    mgr = get_job_manager()
    state = mgr.get_status(job_id)
    if state is None:
        click.echo(f"Job not found: {job_id}")
        raise SystemExit(1)
    click.echo(f"Job:      {state.job_id}")
    click.echo(f"Status:   {state.status.value}")
    click.echo(f"Progress: {state.progress_pct}%")
    click.echo(f"Step:     {state.current_step}")
    if state.error:
        click.echo(f"Error:    {state.error}")
    if state.result:
        click.echo(f"Result:   {state.result}")


def main():
    """Entry point for corpus-video CLI."""
    video()


if __name__ == "__main__":
    main()
