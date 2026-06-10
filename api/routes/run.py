import os
import sys
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "rga-copilot"))

from job_store import create_job, update_job

router = APIRouter()


@router.post("/run")
async def run_analysis(
    xlsx: UploadFile = File(...),
    qual_docs: list[UploadFile] = File(default=[]),
    period: str = Form(...),
    year: int = Form(...),
    company: str = Form(default="Grupo Nama"),
    break_even_target_ebitda: float = Form(default=1_500_000.0),
):
    job_id = create_job()

    tmp_dir = tempfile.mkdtemp()
    xlsx_bytes = await xlsx.read()
    xlsx_path = os.path.join(tmp_dir, xlsx.filename or "data.xlsx")
    with open(xlsx_path, "wb") as f:
        f.write(xlsx_bytes)

    qual_paths: list[str] = []
    for doc in qual_docs:
        doc_bytes = await doc.read()
        path = os.path.join(tmp_dir, doc.filename or "doc.pdf")
        with open(path, "wb") as f:
            f.write(doc_bytes)
        qual_paths.append(path)

    def _run() -> None:
        try:
            update_job(job_id, "running")
            from orchestrator import run_analysis as _pipeline
            result = _pipeline(
                xlsx_path=xlsx_path,
                year=year,
                qual_docs=qual_paths,
                period=period,
                company=company,
                break_even_target_ebitda=break_even_target_ebitda,
            )
            update_job(job_id, "done", result=result.model_dump(mode="json"))
        except Exception as exc:
            update_job(job_id, "error", error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job_id}
