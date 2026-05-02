"""Tests for MCP video tools."""

from unittest.mock import MagicMock, patch

from mcp_server.tools.video import (
    video_ingest_local,
    video_ingest_url,
    video_job_status,
    video_list_jobs,
)
from tools.video.jobs import JobManager, JobStatus


def _mock_config():
    cfg = MagicMock()
    cfg.to_dict.return_value = {
        "llm": {"endpoint": "http://localhost:11434"},
        "embedding": {}, "database": {}, "paths": {"scratch_dir": "./scratch", "output_dir": "./output"},
        "video": {},
    }
    return cfg


def test_video_ingest_local_file_not_found():
    mgr = JobManager(max_workers=1)
    result = video_ingest_local("/nonexistent/video.mp4", "test", _mock_config(), MagicMock(), mgr)
    assert result["status"] == "error"
    assert "not found" in result["error"]


@patch("mcp_server.tools.video.Path")
def test_video_ingest_local_submits_job(mock_path):
    mock_path.return_value.exists.return_value = True
    mgr = MagicMock()
    mgr.submit.return_value = "abc123"
    result = video_ingest_local("/tmp/test.mp4", "notes", _mock_config(), MagicMock(), mgr)
    assert result["status"] == "submitted"
    assert result["job_id"] == "abc123"


def test_video_ingest_url_submits_job():
    mgr = MagicMock()
    mgr.submit.return_value = "def456"
    result = video_ingest_url("https://youtube.com/watch?v=abc", "notes", _mock_config(), MagicMock(), mgr)
    assert result["status"] == "submitted"
    assert result["job_id"] == "def456"


def test_video_job_status_found():
    mgr = JobManager(max_workers=1)
    def work(cb): return {"ok": True}
    job_id = mgr.submit(work)
    import time; time.sleep(0.5)
    result = video_job_status(job_id, mgr)
    assert result["status"] == "complete"


def test_video_job_status_not_found():
    mgr = JobManager(max_workers=1)
    result = video_job_status("nonexistent", mgr)
    assert result["status"] == "error"


def test_video_list_jobs_empty():
    mgr = JobManager(max_workers=1)
    result = video_list_jobs(mgr)
    assert result["status"] == "success"
    assert result["jobs"] == []



def test_video_response_no_full_paths():
    """Verify MCP responses don't leak full filesystem paths."""
    from mcp_server.tools.video import video_job_status
    from tools.video.jobs import JobManager
    mgr = JobManager(max_workers=1)
    def work(cb):
        return {"output_path": "just_a_name.md"}
    job_id = mgr.submit(work)
    import time; time.sleep(0.5)
    result = video_job_status(job_id, mgr)
    # Result should not contain backslashes or drive letters
    result_str = str(result)
    assert "C:\\" not in result_str
    assert "/home/" not in result_str
