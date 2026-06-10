import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from job_store import create_job, get_job, update_job


def test_create_job_returns_uuid():
    job_id = create_job()
    assert len(job_id) == 36
    assert job_id.count("-") == 4


def test_new_job_status_is_pending():
    job_id = create_job()
    job = get_job(job_id)
    assert job["status"] == "pending"
    assert job["result"] is None
    assert job["error"] is None


def test_update_job_running():
    job_id = create_job()
    update_job(job_id, "running")
    assert get_job(job_id)["status"] == "running"


def test_update_job_done_with_result():
    job_id = create_job()
    update_job(job_id, "done", result={"key": "value"})
    job = get_job(job_id)
    assert job["status"] == "done"
    assert job["result"] == {"key": "value"}


def test_get_nonexistent_job_returns_none():
    assert get_job("does-not-exist") is None
