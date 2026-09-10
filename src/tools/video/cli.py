"""CLI interface for video tool."""

from pathlib import Path

import click


def __getattr__(name: str):
    """Lazily provide heavy symbols on attribute access.

    Keeps ``corpus tools video --help`` from importing the transcription /
    cleaning / augmentation stack (Whisper, torch, etc.). Symbols are exposed
    lazily so patching (e.g. ``patch("tools.video.cli.VideoTranscriber")``) and
    normal attribute access still resolve the real implementation.
    """
    if name == "load_cli_config":
        from cli_common import load_cli_config

        return load_cli_config
    if name == "VideoConfig":
        from .config import VideoConfig

        return VideoConfig
    if name == "VideoTranscriber":
        from .transcribe import VideoTranscriber

        return VideoTranscriber
    if name == "TranscriptCleaner":
        from .clean import TranscriptCleaner

        return TranscriptCleaner
    if name == "TranscriptAugmenter":
        from .augment import TranscriptAugmenter

        return TranscriptAugmenter
    if name == "discover_media_files":
        from .discover import discover_media_files

        return discover_media_files
    if name == "run_transcription_queue":
        from .pipeline_queue import run_transcription_queue

        return run_transcription_queue
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _resolve(name: str):
    """Resolve a possibly patched symbol without eagerly importing implementations."""
    try:
        return globals()[name]
    except KeyError:
        return __getattr__(name)


def _default_workers(cfg) -> int:
    """Resolve the default worker count from config (``max_concurrent_jobs``)."""
    from tools.video.pipeline_queue import clamp_workers

    return clamp_workers(getattr(cfg, "max_concurrent_jobs", 1) or 1)


def _output_subdir(root: Path, parent: Path) -> Path:
    """Relative path of ``parent`` under the discovery ``root``, without ``..``.

    Used to namespace generated transcripts under configured output/scratch
    dirs instead of writing into the source lecture folder.
    """
    try:
        rel = parent.resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(parent.name)
    parts = [p for p in rel.parts if p not in ("", ".", "..")]
    return Path(*parts) if parts else Path(parent.name)


def _ensure_under(path: Path, root: Path) -> Path:
    """Resolve ``path`` and refuse it if it escapes ``root``."""
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise click.ClickException(f"Refusing to write outside {root}: {resolved}")
    return resolved


def _cleaned_transcript_name(lecture_dir: Path) -> str:
    """Filename for a cleaned transcript, derived from the lecture folder.

    ``P1L1`` → ``p1l1_transcript.md``. Unsafe characters are replaced so the
    name cannot escape the scratch directory.
    """
    raw = lecture_dir.name.strip().lower().replace("..", "_")
    pieces = []
    current: list[str] = []
    for char in raw:
        if char.isalnum() or char in "-_":
            current.append(char)
        else:
            if current:
                pieces.append("".join(current))
                current = []
    if current:
        pieces.append("".join(current))
    stem = "_".join(pieces) or "lecture"
    return f"{stem}_transcript.md"


def _run_queue(cfg, files, *, skip_clean: bool, workers: int):
    """Construct shared transcriber/cleaner and drain the transcription queue.

    Echoes ``Queued N videos...`` *before* constructing the ``VideoTranscriber``
    so users see the work size even while the (heavy) Whisper stack loads. A
    single shared cleaner is built only when cleaning is actually required
    (``skip_clean`` is False), and the same cleaned payload it produces is what
    callers persist — the queue never triggers a second cleaner pass.

    Returns the list of ``TranscriptJobResult`` in input order.
    """
    VideoTranscriber = _resolve("VideoTranscriber")
    run_transcription_queue = _resolve("run_transcription_queue")
    from tools.video.pipeline_queue import clamp_workers

    click.echo(f"Queued {len(files)} videos...")

    transcriber = VideoTranscriber(cfg)
    cleaner = None
    if not skip_clean:
        cleaner = _resolve("TranscriptCleaner")(cfg)

    return run_transcription_queue(
        files,
        transcriber=transcriber,
        cleaner=cleaner,
        skip_clean=skip_clean,
        max_workers=clamp_workers(workers),
    )


def _group_by_parent(results):
    """Group queue results by their ``parent`` directory, preserving order.

    Returns an ordered ``dict`` mapping ``parent -> [result, ...]``. Only the
    caller decides which results (e.g. successes) to feed in.
    """
    grouped: dict = {}
    for result in results:
        grouped.setdefault(result.parent, []).append(result)
    return grouped


def _combine_group(transcriber, group, *, use_cleaned: bool, course, lecture) -> str:
    """Combine a per-parent group of results into one markdown document.

    Reuses ``VideoTranscriber.combine_transcripts`` by building the
    ``filename -> text`` mapping it expects. When ``use_cleaned`` is True the
    cleaned payload from the queue is used (falling back to raw if a file was
    not cleaned); otherwise the raw transcript is used.
    """
    transcripts = {}
    for result in group:
        text = result.cleaned if use_cleaned else result.raw
        if text is None:
            text = result.raw or ""
        transcripts[result.source.name] = text
    return transcriber.combine_transcripts(transcripts, course, lecture)


def _report_results(results) -> int:
    """Emit per-file success/failure lines. Returns the count of failures."""
    failures = 0
    for result in results:
        if result.error is None:
            click.echo(f"  ✓ {result.source.name}")
        else:
            failures += 1
            click.echo(f"  ✗ {result.source.name}: {result.error}")
    return failures


def _is_single_folder(root: Path, grouped) -> bool:
    """Decide whether legacy single-folder output paths apply.

    Legacy applies when discovery produced at most one parent group *and* that
    group is the input itself — a single input file, or a directory whose direct
    children are the discovered media. A nested tree (files living in
    subdirectories) always uses per-parent output instead.
    """
    if len(grouped) > 1:
        return False
    if not grouped:
        return True
    if root.is_file():
        return True
    sole_parent = next(iter(grouped)).resolve()
    return sole_parent == root.resolve()


@click.group()
def video():
    """Video transcription and processing tool."""
    pass


@video.command()
@click.argument("input_folder", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file (single-folder legacy path)")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--course", "-c", default=None, help="Course identifier (e.g., BIOL101)")
@click.option("--lecture", "-l", default=None, type=int, help="Lecture number")
@click.option("--clean", is_flag=True, help="Run LLM cleaning after transcription")
@click.option(
    "--no-recursive",
    "no_recursive",
    is_flag=True,
    help="Only scan the top-level folder (default recurses)",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Concurrent workers (defaults to config max_concurrent_jobs)",
)
def transcribe(
    input_folder: str,
    output: str,
    config: str,
    course: str,
    lecture: int,
    clean: bool,
    no_recursive: bool,
    workers: int,
):
    """Transcribe video files to text.

    Discovers media files under ``input_folder`` (recursively by default),
    transcribes them through the shared, dependency-safe queue, and combines
    results per parent directory. A single-folder input keeps the legacy output
    path; a nested tree writes one transcript per parent directory.
    """
    load_cli_config = _resolve("load_cli_config")
    VideoConfig = _resolve("VideoConfig")
    discover_media_files = _resolve("discover_media_files")
    cfg = load_cli_config(config, VideoConfig)

    root = Path(input_folder)
    recursive = not no_recursive
    resolved_workers = workers if workers is not None else _default_workers(cfg)

    click.echo(f"Transcribing videos from {input_folder}...")
    files = discover_media_files(root, cfg.supported_extensions, recursive=recursive)

    # skip cleaning unless the user asked for it.
    skip_clean = not clean
    results = _run_queue(cfg, files, skip_clean=skip_clean, workers=resolved_workers)

    failures = _report_results(results)
    successes = [r for r in results if r.error is None]

    # Build a transcriber purely for its (pure) combine helper; the queue owns
    # all model work, so this constructs nothing heavy at combine time.
    VideoTranscriber = _resolve("VideoTranscriber")
    combiner = VideoTranscriber(cfg)

    grouped = _group_by_parent(successes)
    written: list[Path] = []

    # Single-folder legacy behaviour: exactly one parent group whose parent is
    # the input directory itself (or the file's own directory).
    single_folder = _is_single_folder(root, grouped)

    for parent, group in grouped.items():
        combined = _combine_group(
            combiner, group, use_cleaned=clean, course=course, lecture=lecture
        )
        if single_folder:
            if output:
                output_path = Path(output)
            elif course and lecture:
                output_path = cfg.paths.output_dir / f"{course}_Lecture{lecture:02d}_transcript.md"
            else:
                output_path = cfg.paths.output_dir / "transcript.md"
        else:
            # Tree mode: one transcript per parent, under configured output_dir.
            subdir = _output_subdir(root, parent)
            output_path = cfg.paths.output_dir / subdir / "transcript.md"
            _ensure_under(output_path, cfg.paths.output_dir)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(combined, encoding="utf-8")
        written.append(output_path)
        click.echo(f"✓ Transcribed {len(group)} videos to {output_path}")

    if failures:
        click.echo(f"✗ {failures} file(s) failed", err=True)
        raise SystemExit(1)



@video.command()
@click.argument("transcript_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def clean(transcript_file: str, output: str, config: str):
    """Clean a raw transcript using LLM."""
    load_cli_config = _resolve("load_cli_config")
    VideoConfig = _resolve("VideoConfig")
    TranscriptCleaner = _resolve("TranscriptCleaner")
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
    load_cli_config = _resolve("load_cli_config")
    VideoConfig = _resolve("VideoConfig")
    TranscriptAugmenter = _resolve("TranscriptAugmenter")
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
@click.option("--output", "-o", default=None, help="Final output file (single-folder legacy path)")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
@click.option("--course", "-c", default=None, help="Course identifier")
@click.option("--lecture", "-l", default=None, type=int, help="Lecture number")
@click.option("--skip-clean", is_flag=True, help="Skip cleaning step")
@click.option("--augment", is_flag=True, help="Open editor for manual augmentation")
@click.option(
    "--no-recursive",
    "no_recursive",
    is_flag=True,
    help="Only scan the top-level folder (default recurses)",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Concurrent workers (defaults to config max_concurrent_jobs)",
)
def pipeline(
    input_folder: str,
    output: str,
    config: str,
    course: str,
    lecture: int,
    skip_clean: bool,
    augment: bool,
    no_recursive: bool,
    workers: int,
):
    """Run complete video processing pipeline.

    Discovery + the shared queue produce raw (and, unless ``--skip-clean``,
    cleaned) transcripts in a single drain — the cleaned payload from the queue
    is what gets written, so no second cleaner pass is triggered. Augmentation,
    when requested, runs serially per combined output after the queue drains.
    """
    load_cli_config = _resolve("load_cli_config")
    VideoConfig = _resolve("VideoConfig")
    discover_media_files = _resolve("discover_media_files")
    cfg = load_cli_config(config, VideoConfig)

    root = Path(input_folder)
    recursive = not no_recursive
    resolved_workers = workers if workers is not None else _default_workers(cfg)

    # Step 1: Transcribe (+ clean inside the queue unless skipped).
    click.echo("Step 1: Transcribing...")
    files = discover_media_files(root, cfg.supported_extensions, recursive=recursive)
    results = _run_queue(cfg, files, skip_clean=skip_clean, workers=resolved_workers)

    failures = _report_results(results)
    successes = [r for r in results if r.error is None]

    VideoTranscriber = _resolve("VideoTranscriber")
    combiner = VideoTranscriber(cfg)

    grouped = _group_by_parent(successes)
    single_folder = _is_single_folder(root, grouped)

    # Derive name from input folder if no course/lecture specified (legacy).
    folder_name = root.resolve().name
    if course and lecture:
        legacy_scratch = cfg.paths.scratch_dir / f"{course}_Lecture{lecture:02d}"
    else:
        legacy_scratch = cfg.paths.scratch_dir / "video" / folder_name

    final_outputs: list[Path] = []

    for parent, group in grouped.items():
        # Where per-parent artifacts live.
        if single_folder:
            scratch = legacy_scratch
        else:
            subdir = _output_subdir(root, parent)
            scratch = cfg.paths.scratch_dir / "video" / subdir
            _ensure_under(scratch, cfg.paths.scratch_dir)
        scratch.mkdir(parents=True, exist_ok=True)

        # Raw transcript always written from the queue's raw payload.
        raw_combined = _combine_group(
            combiner, group, use_cleaned=False, course=course, lecture=lecture
        )
        raw_transcript = scratch / "transcript_raw.md"
        raw_transcript.write_text(raw_combined, encoding="utf-8")
        click.echo(f"✓ Raw transcript: {raw_transcript}")
        current_file = raw_transcript

        # Cleaned transcript uses the queue's cleaned payload — no 2nd cleaner.
        if not skip_clean:
            cleaned_combined = _combine_group(
                combiner, group, use_cleaned=True, course=course, lecture=lecture
            )
            cleaned_path = scratch / _cleaned_transcript_name(parent)
            cleaned_path.write_text(cleaned_combined, encoding="utf-8")
            click.echo(f"✓ Cleaned transcript: {cleaned_path}")
            current_file = cleaned_path

        final_outputs.append((parent, scratch, current_file))

    # Step: Augment (serial, per output, after the queue has fully drained).
    if augment:
        click.echo("\nAugmenting...")
        augmenter = _resolve("TranscriptAugmenter")(cfg)
        augmented: list = []
        for parent, scratch, current_file in final_outputs:
            if single_folder and output:
                final_path = Path(output)
            elif course and lecture:
                final_path = scratch / f"{course}_Lecture{lecture:02d}_final.md"
            else:
                final_path = scratch / "transcript_final.md"
            result_path = augmenter.augment(current_file, final_path, auto_save=False)
            augmented.append((parent, scratch, result_path))
        final_outputs = augmented

    for _parent, _scratch, out in final_outputs:
        click.echo(f"✓ Pipeline output: {out}")

    if failures:
        click.echo(f"✗ {failures} file(s) failed", err=True)
        raise SystemExit(1)

    click.echo("\n✓ Pipeline complete!")



@video.command("ingest")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("--collection", "-c", required=True, help="Target collection")
@click.option(
    "--threshold",
    default=None,
    type=float,
    help="Scene detection sensitivity (0.0-1.0)",
)
@click.option("--model", default=None, help="Ollama vision model for OCR")
@click.option("--no-latex", is_flag=True, help="Disable pix2tex math fallback")
@click.option("--context-window", default=None, type=int, help="Adjacent frames per chunk")
@click.option("--keep-frames", is_flag=True, help="Keep extracted frames after ingest")
@click.option("--config", "-f", default="configs/base.yaml", help="Config file")
def ingest_cmd(
    video_path,
    collection,
    threshold,
    model,
    no_latex,
    context_window,
    keep_frames,
    config,
):
    """Ingest a video file using visual OCR pipeline."""
    from tools.video.ingest import ingest_video

    load_cli_config = _resolve("load_cli_config")
    VideoConfig = _resolve("VideoConfig")
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
            video_path,
            cfg,
            output_dir=cfg.paths.output_dir / "video_ocr",
            progress_cb=progress_cb,
            scene_threshold=threshold,
            vision_model=model,
            use_latex_fallback=not no_latex if no_latex else None,
            context_window=context_window,
            cleanup_frames=not keep_frames,
        )

    click.echo("\n\u2713 Ingest complete")
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

    load_cli_config = _resolve("load_cli_config")
    VideoConfig = _resolve("VideoConfig")
    cfg = load_cli_config(config, VideoConfig)
    dl_dir = cfg.paths.scratch_dir / "downloads"

    click.echo(f"Downloading {url}...")
    dl_result = download_video(url, dl_dir)
    click.echo(f"\u2713 Downloaded: {dl_result.title} ({dl_result.duration_sec:.0f}s)")

    click.echo("Ingesting via visual OCR...")
    with click.progressbar(length=100, label="Processing") as bar:
        last_pct = [0]

        def progress_cb(pct, step):
            delta = pct - last_pct[0]
            if delta > 0:
                bar.update(delta)
                last_pct[0] = pct

        result = ingest_video(
            dl_result.local_path,
            cfg,
            output_dir=cfg.paths.output_dir / "video_ocr",
            progress_cb=progress_cb,
            scene_threshold=threshold,
            vision_model=model,
        )

    click.echo("\n\u2713 Ingest complete")
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
