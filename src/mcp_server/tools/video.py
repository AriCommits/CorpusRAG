"""Video MCP tool implementations."""

from __future__ import annotations

from pathlib import Path

from config import BaseConfig
from db import DatabaseBackend


def video_ingest_local(
    path: str, collection: str, config: BaseConfig, db: DatabaseBackend,
    job_manager, vision_model: str | None = None, scene_threshold: float | None = None,
) -> dict:
    """Ingest a local video file via visual OCR pipeline (async)."""
    from tools.video.config import VideoConfig
    from tools.video.ingest import ingest_video

    video_path = Path(path)
    if not video_path.exists():
        return {"status": "error", "error": f"File not found: {path}"}

    video_config = VideoConfig.from_dict(config.to_dict())
    output_dir = video_config.paths.output_dir / "video_ocr"

    def _run(progress_cb):
        result = ingest_video(
            video_path, video_config, output_dir=output_dir,
            progress_cb=progress_cb,
            vision_model=vision_model, scene_threshold=scene_threshold,
        )
        return {
            "status": "success",
            "source_file": Path(result.source_file).name,
            "frames_extracted": result.frames_extracted,
            "frames_skipped": result.frames_skipped,
            "chunks": result.chunks_after_dedup,
            "duration_sec": result.duration_sec,
            "output_path": result.output_path.name if result.output_path else None,
        }

    job_id = job_manager.submit(_run)
    return {"status": "submitted", "job_id": job_id}


def video_ingest_url(
    url: str, collection: str, config: BaseConfig, db: DatabaseBackend,
    job_manager, vision_model: str | None = None, scene_threshold: float | None = None,
) -> dict:
    """Download video from URL then run visual OCR pipeline (async)."""
    from tools.video.config import VideoConfig
    from tools.video.download import download_video
    from tools.video.ingest import ingest_video

    video_config = VideoConfig.from_dict(config.to_dict())
    output_dir = video_config.paths.output_dir / "video_ocr"
    dl_dir = video_config.paths.scratch_dir / "downloads"

    def _run(progress_cb):
        progress_cb(0, "Downloading video")
        dl_result = download_video(url, dl_dir)
        progress_cb(10, f"Downloaded: {dl_result.title}")

        def scaled_cb(pct, step):
            progress_cb(10 + int(pct * 0.9), step)

        result = ingest_video(
            dl_result.local_path, video_config, output_dir=output_dir,
            progress_cb=scaled_cb,
            vision_model=vision_model, scene_threshold=scene_threshold,
        )
        return {
            "status": "success",
            "source_file": Path(result.source_file).name,
            "title": dl_result.title,
            "frames_extracted": result.frames_extracted,
            "chunks": result.chunks_after_dedup,
            "output_path": result.output_path.name if result.output_path else None,
        }

    job_id = job_manager.submit(_run)
    return {"status": "submitted", "job_id": job_id}


def video_combined_pipeline(
    path_or_url: str, collection: str, config: BaseConfig, db: DatabaseBackend,
    job_manager, include_audio: bool = True, include_visual: bool = True,
) -> dict:
    """Combined audio+visual pipeline (async)."""
    from concurrent.futures import ThreadPoolExecutor
    from tools.video.config import VideoConfig
    from tools.video.download import download_video, is_url
    from tools.video.ingest import ingest_video

    video_config = VideoConfig.from_dict(config.to_dict())
    output_dir = video_config.paths.output_dir / "video_combined"

    def _run(progress_cb):
        if is_url(path_or_url):
            progress_cb(0, "Downloading")
            dl = download_video(path_or_url, video_config.paths.scratch_dir / "downloads")
            video_path = dl.local_path
            progress_cb(10, f"Downloaded: {dl.title}")
        else:
            video_path = Path(path_or_url)
            if not video_path.exists():
                raise FileNotFoundError(f"File not found: {path_or_url}")

        results = {}

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {}
            if include_visual:
                futures["visual"] = pool.submit(
                    ingest_video, video_path, video_config, output_dir,
                )
            if include_audio:
                def _transcribe():
                    from tools.video.transcribe import VideoTranscriber
                    from tools.video.clean import TranscriptCleaner
                    transcriber = VideoTranscriber(video_config)
                    raw = transcriber.transcribe_file(video_path)
                    cleaner = TranscriptCleaner(video_config)
                    return cleaner.clean(raw)
                futures["audio"] = pool.submit(_transcribe)

            progress_cb(50, "Processing audio and visual")

            for key, future in futures.items():
                results[key] = future.result()

        progress_cb(90, "Merging results")

        output = {"status": "success", "tracks": []}
        if "visual" in results:
            vr = results["visual"]
            output["visual_chunks"] = vr.chunks_after_dedup
            output["output_path"] = vr.output_path.name if vr.output_path else None
            output["tracks"].append("visual")
        if "audio" in results:
            output["audio_transcript"] = results["audio"][:500] + "..." if len(results["audio"]) > 500 else results["audio"]
            output["tracks"].append("audio")
            output_dir.mkdir(parents=True, exist_ok=True)
            audio_path = output_dir / f"{video_path.stem}_audio.md"
            audio_path.write_text(results["audio"], encoding="utf-8")
            output["audio_path"] = audio_path.name

        progress_cb(100, "Complete")
        return output

    job_id = job_manager.submit(_run)
    return {"status": "submitted", "job_id": job_id}


def video_job_status(job_id: str, job_manager) -> dict:
    """Get status of a video processing job."""
    state = job_manager.get_status(job_id)
    if state is None:
        return {"status": "error", "error": f"Job not found: {job_id}"}
    return state.to_dict()


def video_list_jobs(job_manager) -> dict:
    """List all video processing jobs."""
    jobs = job_manager.list_jobs()
    return {"status": "success", "jobs": [j.to_dict() for j in jobs]}
