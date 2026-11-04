"""DEV-ONLY in-memory backend for local development (TK-002).

Active only when BEOSABASI_FAKE=1 (see api.main). Implements just enough of
contracts/openapi.yaml for the fake-worker loop over plain HTTP with no R2,
no GPU, and no Cloudflare:

  POST /dev/jobs                     seed one queued job (dev shortcut)
  POST /worker/v1/jobs/claim         FIFO claim with 5-minute lease
  POST /worker/v1/jobs/{id}/heartbeat  renew lease, report stage, honor cancel
  POST /worker/v1/jobs/{id}/result   store segments/speakers -> completed
  POST /worker/v1/jobs/{id}/fail     attempts+1, requeue (max 3) or failed
  POST /worker/v1/ping               registration + minimum-version check
  GET  /api/jobs/{id}                status + queue position + ETA
  GET  /api/jobs/{id}/transcript     stored segments/speakers (empty until done)

Real routers from TK-020+ replace these paths. Nothing here touches disk,
R2, or real auth. Do NOT enable outside local development.
"""

import time
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas import (
    Ack,
    ClaimResponse,
    Heartbeat,
    HeartbeatResponse,
    Job,
    JobDetail,
    JobState,
    KodeGalat,
    Transcript,
    WorkerFail,
    WorkerPing,
    WorkerPingResponse,
    WorkerResult,
)

router = APIRouter()

LEASE_SECONDS = 5 * 60
MAX_ATTEMPTS = 3
MIN_WORKER_VERSION = "0.1.0"

_jobs: dict = {}


def reset() -> None:
    """Clear all fake state (tests, dev restarts)."""
    _jobs.clear()


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+07:00", time.localtime(ts))


def _requeue_expired() -> None:
    for job in _jobs.values():
        if job["state"] == JobState.PROCESSING and _now() > job["lease_until"]:
            job["attempts"] += 1
            if job["attempts"] >= MAX_ATTEMPTS:
                job["state"] = JobState.FAILED
                job["error_code"] = KodeGalat.LEASE_LOST
            else:
                job["state"] = JobState.QUEUED
                job["lease_until"] = 0.0


def _get(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job tidak ditemukan")
    return job


def _job_view(job: dict) -> Job:
    return Job(
        job_id=job["job_id"],
        state=job["state"],
        stage=job["stage"],
        filename=job["filename"],
        size_bytes=job["size_bytes"],
        duration_seconds=job["duration_seconds"],
        language=job["language"],
        diarization=job["diarization"],
        billed_minutes=job["billed_minutes"],
        attempts=job["attempts"],
        error_code=job["error_code"],
        created_at=job["created_at"],
        finished_at=job["finished_at"],
    )


class DevJobSeed(BaseModel):
    language: str = "id"
    diarization: bool = False
    duration_seconds: float = 60.0


@router.post("/dev/jobs", response_model=Job, status_code=201)
def dev_seed_job(seed: DevJobSeed) -> Job:
    """Dev shortcut: create one queued job without uploads/R2/auth."""
    job_id = str(uuid.uuid4())
    now = _now()
    job = {
        "job_id": job_id,
        "state": JobState.QUEUED,
        "stage": None,
        "filename": "contoh-lokal.wav",
        "size_bytes": 0,
        "duration_seconds": seed.duration_seconds,
        "language": seed.language,
        "diarization": seed.diarization,
        "billed_minutes": seed.duration_seconds / 60.0 * (2.0 if seed.diarization else 1.0),
        "attempts": 0,
        "error_code": None,
        "created_at": _iso(now),
        "created_ts": now,
        "finished_at": None,
        "lease_until": 0.0,
        "segments": [],
        "speakers": [],
        "cancelled": False,
    }
    _jobs[job_id] = job
    return _job_view(job)


@router.post("/worker/v1/jobs/claim", response_model=ClaimResponse, status_code=200)
def worker_claim(wait: int = Query(default=25, ge=0, le=25)):
    _requeue_expired()
    queued = sorted(
        (j for j in _jobs.values() if j["state"] == JobState.QUEUED),
        key=lambda j: j["created_ts"],
    )
    if not queued:
        if wait > 0:
            time.sleep(min(wait, 2))
            _requeue_expired()
            queued = sorted(
                (j for j in _jobs.values() if j["state"] == JobState.QUEUED),
                key=lambda j: j["created_ts"],
            )
        if not queued:
            from fastapi import Response

            return Response(status_code=204)
    job = queued[0]
    job["state"] = JobState.PROCESSING
    job["stage"] = None
    job["attempts"] += 1
    job["lease_until"] = _now() + LEASE_SECONDS
    return ClaimResponse(
        job_id=job["job_id"],
        audio_url=f"fake://local/{job['job_id']}",
        audio_expires_at=_iso(_now() + 15 * 60),
        language=job["language"],
        diarization=job["diarization"],
        min_speakers=None,
        max_speakers=None,
        lease_until=_iso(job["lease_until"]),
    )


@router.post("/worker/v1/jobs/{job_id}/heartbeat", response_model=HeartbeatResponse)
def worker_heartbeat(job_id: str, body: Heartbeat) -> HeartbeatResponse:
    job = _get(job_id)
    if job["state"] != JobState.PROCESSING or _now() > job["lease_until"]:
        raise HTTPException(status_code=409, detail="sewa hilang")
    job["stage"] = body.stage
    job["lease_until"] = _now() + LEASE_SECONDS
    return HeartbeatResponse(cancel=job["cancelled"], lease_until=_iso(job["lease_until"]))


@router.post("/worker/v1/jobs/{job_id}/result", response_model=Ack)
def worker_result(job_id: str, body: WorkerResult) -> Ack:
    job = _get(job_id)
    if job["state"] != JobState.PROCESSING or _now() > job["lease_until"]:
        raise HTTPException(status_code=409, detail="sewa hilang")
    job["segments"] = [s.model_dump() for s in body.segments]
    job["speakers"] = [s.model_dump() for s in body.speakers]
    job["diarization_available"] = bool(body.speakers)
    job["state"] = JobState.COMPLETED
    job["finished_at"] = _iso(_now())
    return Ack(ok=True)


@router.post("/worker/v1/jobs/{job_id}/fail", response_model=Ack)
def worker_fail(job_id: str, body: WorkerFail) -> Ack:
    job = _get(job_id)
    if body.retryable and job["attempts"] < MAX_ATTEMPTS:
        job["state"] = JobState.QUEUED
        job["lease_until"] = 0.0
    else:
        job["state"] = JobState.FAILED
        job["error_code"] = body.code
        job["finished_at"] = _iso(_now())
    return Ack(ok=True)


@router.post("/worker/v1/ping", response_model=WorkerPingResponse)
def worker_ping(body: WorkerPing) -> WorkerPingResponse:
    return WorkerPingResponse(ok=True, min_version=MIN_WORKER_VERSION,
                              update_required=False)


@router.get("/api/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str) -> JobDetail:
    job = _get(job_id)
    ahead = sum(
        1 for j in _jobs.values()
        if j["state"] == JobState.QUEUED and j["created_ts"] < job["created_ts"]
    )
    active = any(j["state"] == JobState.PROCESSING for j in _jobs.values())
    position = ahead + (1 if job["state"] == JobState.QUEUED else 0)
    eta = (position * (job["duration_seconds"] or 60.0) / 8.0) if position else None
    return JobDetail(job=_job_view(job), queue_position=position or None,
                     eta_seconds=eta, worker_active=active)


@router.get("/api/jobs/{job_id}/transcript", response_model=Transcript)
def get_transcript(job_id: str) -> Transcript:
    job = _get(job_id)
    return Transcript(job_id=job_id, segments=job["segments"], speakers=job["speakers"])
