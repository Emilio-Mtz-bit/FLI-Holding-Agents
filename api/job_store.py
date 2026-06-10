import threading
import uuid
from typing import Any

# TODO: replace _store with Redis or a database for multi-worker deployments.
# This in-process dict is invisible across Gunicorn worker processes.
_store: dict[str, dict] = {}
_lock = threading.Lock()


def create_job() -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _store[job_id] = {"status": "pending", "result": None, "error": None}
    return job_id


def update_job(job_id: str, status: str, result: Any = None, error: str | None = None) -> None:
    with _lock:
        _store[job_id] = {"status": status, "result": result, "error": error}


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _store.get(job_id)
