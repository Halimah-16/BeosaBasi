"""TK-002: --fake worker mode (sample WAV + fake HTTP run)."""

import wave

import httpx

from worker import cli
from worker.cli import build_parser


def test_parser_has_fake_commands():
    args = build_parser().parse_args(["run", "--fake", "--once"])
    assert args.command == "run" and args.fake and args.once
    args = build_parser().parse_args(["demo"])
    assert args.command == "demo"
    args = build_parser().parse_args(["make-sample", "--seconds", "2"])
    assert args.seconds == 2


def test_make_sample_wav_is_valid(tmp_path):
    path = str(tmp_path / "hening.wav")
    cli.make_sample_wav(path, seconds=2)
    with wave.open(path, "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16000
        assert wav.getnframes() == 32000


def test_run_fake_once_completes_job():
    posted = {}

    claim = {
        "job_id": "00000000-0000-4000-8000-000000000001",
        "audio_url": "fake://local/00000000-0000-4000-8000-000000000001",
        "audio_expires_at": "2026-11-02T08:00:00+07:00",
        "language": "id",
        "diarization": True,
        "min_speakers": None,
        "max_speakers": None,
        "lease_until": "2026-11-02T08:05:00+07:00",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/worker/v1/jobs/claim":
            return httpx.Response(200, json=claim)
        if request.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={"cancel": False,
                                             "lease_until": claim["lease_until"]})
        if request.url.path.endswith("/result"):
            import json as _json
            posted["result"] = _json.loads(request.content.decode())
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler),
                          base_url="http://fake")
    job_id = cli.run_fake_once(client, wait=0, process_seconds=0.01)
    assert job_id == claim["job_id"]
    assert len(posted["result"]["segments"]) == 2
    assert posted["result"]["speakers"][0]["display_name"] == "Dina"


def test_run_fake_once_empty_queue():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler),
                          base_url="http://fake")
    assert cli.run_fake_once(client, wait=0) is None
