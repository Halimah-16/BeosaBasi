"""TK-002: fake backend round-trip over HTTP (no R2, GPU, or Cloudflare)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import fake


@pytest.fixture()
def client():
    fake.reset()
    app = FastAPI()
    app.include_router(fake.router)
    return TestClient(app)


def test_seed_claim_heartbeat_result_transcript(client):
    job = client.post("/dev/jobs", json={"language": "id", "diarization": True}).json()
    assert job["state"] == "queued"
    job_id = job["job_id"]

    claimed = client.post("/worker/v1/jobs/claim?wait=0")
    assert claimed.status_code == 200
    assert claimed.json()["job_id"] == job_id

    beat = client.post(f"/worker/v1/jobs/{job_id}/heartbeat",
                       json={"stage": "transcribing"}).json()
    assert beat["cancel"] is False

    result = {
        "segments": [{
            "index": 0, "start": 0.0, "end": 4.2, "text": "selamat pagi",
            "confidence": 0.93, "speaker_id": "spk1",
            "edited": False, "version": 1,
        }],
        "speakers": [{"speaker_id": "spk1", "label": "Pembicara 1",
                      "display_name": "Dina"}],
        "duration_seconds": 60.0,
        "xrt": 8.0,
        "model_version": "fake-0.1.0",
        "low_confidence_ratio": 0.0,
    }
    assert client.post(f"/worker/v1/jobs/{job_id}/result", json=result).json() == {"ok": True}

    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["job"]["state"] == "completed"
    transcript = client.get(f"/api/jobs/{job_id}/transcript").json()
    assert transcript["segments"][0]["text"] == "selamat pagi"
    assert transcript["speakers"][0]["display_name"] == "Dina"


def test_claim_empty_queue_returns_204(client):
    assert client.post("/worker/v1/jobs/claim?wait=0").status_code == 204


def test_retryable_fail_requeues_then_fails(client):
    job_id = client.post("/dev/jobs", json={}).json()["job_id"]
    client.post("/worker/v1/jobs/claim?wait=0")
    client.post(f"/worker/v1/jobs/{job_id}/fail",
                json={"code": "FFMPEG_ERROR", "retryable": True})
    assert client.get(f"/api/jobs/{job_id}").json()["job"]["state"] == "queued"
    for _ in range(3):
        client.post("/worker/v1/jobs/claim?wait=0")
        client.post(f"/worker/v1/jobs/{job_id}/fail",
                    json={"code": "FFMPEG_ERROR", "retryable": True})
    assert client.get(f"/api/jobs/{job_id}").json()["job"]["state"] == "failed"
