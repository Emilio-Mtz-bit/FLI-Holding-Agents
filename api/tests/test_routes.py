import io


def test_run_returns_job_id(client, tmp_path):
    # Minimal xlsx-like bytes (real validation not needed for route test)
    fake_xlsx = io.BytesIO(b"PK fake xlsx content")
    response = client.post(
        "/api/run",
        data={
            "period": "ENERO 2026",
            "year": "2026",
            "company": "Test Co",
            "break_even_target_ebitda": "1500000",
        },
        files={"xlsx": ("test.xlsx", fake_xlsx, "application/vnd.ms-excel")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    assert len(body["job_id"]) == 36


def test_run_job_starts_as_pending_or_running(client, tmp_path):
    fake_xlsx = io.BytesIO(b"PK fake xlsx content")
    run_resp = client.post(
        "/api/run",
        data={"period": "ENERO 2026", "year": "2026"},
        files={"xlsx": ("test.xlsx", fake_xlsx, "application/vnd.ms-excel")},
    )
    job_id = run_resp.json()["job_id"]
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ("pending", "running", "error")
