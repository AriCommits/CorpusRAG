"""Tests for async job manager."""

import time

from tools.video.jobs import JobManager, JobStatus


def test_submit_and_complete():
    mgr = JobManager(max_workers=1)
    def work(progress_cb):
        progress_cb(50, "halfway")
        return {"done": True}
    job_id = mgr.submit(work)
    time.sleep(0.5)
    state = mgr.get_status(job_id)
    assert state is not None
    assert state.status == JobStatus.COMPLETE
    assert state.result == {"done": True}
    assert state.progress_pct == 100


def test_submit_failure():
    mgr = JobManager(max_workers=1)
    def fail(progress_cb):
        raise ValueError("boom")
    job_id = mgr.submit(fail)
    time.sleep(0.5)
    state = mgr.get_status(job_id)
    assert state.status == JobStatus.FAILED
    assert "boom" in state.error


def test_list_jobs():
    mgr = JobManager(max_workers=2)
    def noop(progress_cb):
        return {}
    mgr.submit(noop)
    mgr.submit(noop)
    time.sleep(0.5)
    jobs = mgr.list_jobs()
    assert len(jobs) == 2


def test_get_status_unknown():
    mgr = JobManager()
    assert mgr.get_status("nonexistent") is None


def test_progress_callback():
    mgr = JobManager(max_workers=1)
    def work(progress_cb):
        progress_cb(25, "step1")
        progress_cb(75, "step2")
        return {}
    job_id = mgr.submit(work)
    time.sleep(0.5)
    state = mgr.get_status(job_id)
    assert state.status == JobStatus.COMPLETE


def test_job_state_to_dict():
    mgr = JobManager(max_workers=1)
    def work(progress_cb):
        return {"ok": True}
    job_id = mgr.submit(work)
    time.sleep(0.5)
    state = mgr.get_status(job_id)
    d = state.to_dict()
    assert d["status"] == "complete"
    assert d["job_id"] == job_id
    assert "created_at" in d
