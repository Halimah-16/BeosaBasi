"""TK-001: generated contract models stay importable and validate samples."""

from api import schemas


def test_job_state_covers_lifecycle():
    assert set(schemas.JobState) == {
        "uploading", "queued", "processing", "completed",
        "failed", "expired", "cancelled", "deleted",
    }


def test_worker_result_sample_validates():
    result = schemas.WorkerResult(
        segments=[
            {
                "index": 0,
                "start": 0.0,
                "end": 4.2,
                "text": "selamat pagi",
                "confidence": 0.93,
                "speaker_id": "spk1",
                "edited": False,
                "version": 1,
            }
        ],
        speakers=[
            {"speaker_id": "spk1", "label": "Pembicara 1", "display_name": "Dina"}
        ],
        duration_seconds=60.0,
        xrt=8.0,
        model_version="whisper-large-v3-turbo-ct2-int8",
        low_confidence_ratio=0.1,
    )
    assert result.segments[0].speaker_id == "spk1"
    assert result.speakers[0].display_name == "Dina"


def test_kode_galat_has_user_facing_codes():
    codes = set(schemas.KodeGalat)
    assert {"QUOTA_EXCEEDED", "WORKER_OFFLINE", "GPU_OOM", "AUDIO_GONE"} <= codes
