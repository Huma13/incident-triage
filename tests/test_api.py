import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main


@pytest.fixture
def setup_api(tmp_path, monkeypatch):
    monkeypatch.setattr(
        api_main, "DB_PATH", str(tmp_path / "test_incidents.db")
    )

    class FakeQueue:
        def __init__(self):
            self.jobs = []

        def enqueue(self, *args, **kwargs):
            self.jobs.append((args, kwargs))

    fake_queue = FakeQueue()
    monkeypatch.setattr(api_main, "queue", fake_queue)

    with TestClient(api_main.app) as client:
        yield client, fake_queue


@pytest.fixture
def valid_payload():
    return json.loads(
        Path("evaluation/case_4_1.json").read_text(encoding="utf-8")
    )


def test_invalid_incident_is_quarantined(setup_api, valid_payload):
    client, fake_queue = setup_api

    valid_payload["source_event_id"] = "invalid-service-test"
    valid_payload["service"] = "mysql"

    response = client.post("/api/v1/runs", json=valid_payload)

    assert response.status_code == 422
    assert response.json()["status"] == "rejected"
    assert response.json()["errors"][0]["field"] == "service"
    assert len(fake_queue.jobs) == 0

    conn = api_main.db()
    try:
        row = conn.execute(
            "SELECT raw, errors FROM quarantine ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert json.loads(row[0])["source_event_id"] == "invalid-service-test"
    assert json.loads(row[1])[0]["field"] == "service"


def test_valid_incident_is_queued(setup_api, valid_payload):
    client, fake_queue = setup_api

    valid_payload["source_event_id"] = "api-test-valid-001"

    response = client.post("/api/v1/runs", json=valid_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["run_id"].startswith("INC-")
    assert len(fake_queue.jobs) == 1


def test_duplicate_incident_is_not_queued_twice(setup_api, valid_payload):
    client, fake_queue = setup_api

    valid_payload["source_event_id"] = "api-test-duplicate-001"

    first = client.post("/api/v1/runs", json=valid_payload)
    second = client.post("/api/v1/runs", json=valid_payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["duplicate"] is True
    assert second.json()["run_id"] == first.json()["run_id"]
    assert len(fake_queue.jobs) == 1


def test_unknown_run_returns_404(setup_api):
    client, _ = setup_api

    assert client.get("/api/v1/runs/UNKNOWN").status_code == 404
    assert client.get("/api/v1/runs/UNKNOWN/result").status_code == 404


def test_result_not_ready_returns_409(setup_api):
    client, _ = setup_api

    conn = api_main.db()
    try:
        conn.execute(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
            (
                "INC-TEST-NOT-READY",
                "api-test-not-ready",
                "queued",
                "{}",
                None,
                "2026-11-13T00:00:00+00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    response = client.get("/api/v1/runs/INC-TEST-NOT-READY/result")

    assert response.status_code == 409
    assert response.json()["status"] == "queued"
    assert response.json()["message"] == "Result is not ready yet."


def test_oversized_payload_returns_413(setup_api):
    client, fake_queue = setup_api

    response = client.post(
        "/api/v1/runs",
        content=b"x" * (api_main.MAX_BODY_BYTES + 1),
    )

    assert response.status_code == 413
    assert response.json()["error"] == "payload too large"
    assert len(fake_queue.jobs) == 0
