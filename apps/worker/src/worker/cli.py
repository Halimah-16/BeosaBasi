"""BeosaBasi worker CLI.

Commands:
  doctor                    environment check (full hardware checks in TK-005)
  make-sample               write a 10s silent WAV fixture (stdlib only)
  run --fake                claim and complete jobs with sample output, no GPU
  demo                      seed one dev job (TK-002 fake API) and complete it
"""

import argparse
import platform
import sys
import time
import wave

import httpx

from worker.schemas import ClaimResponse, ProcessingStage

DEFAULT_API_URL = "http://localhost:8000"
SAMPLE_RATE = 16000

# Self-made Indonesian sample lines (TK-002 fixture, no user data).
SAMPLE_LINES = [
    (0.0, 4.2, "selamat pagi, terima kasih sudah bersedia diwawancarai", "spk1", 0.93),
    (4.2, 9.8, "selamat pagi juga, dengan senang hati", "spk2", 0.91),
]

SAMPLE_SPEAKERS = [
    {"speaker_id": "spk1", "label": "Pembicara 1", "display_name": "Dina"},
    {"speaker_id": "spk2", "label": "Pembicara 2", "display_name": "Narasumber"},
]


def doctor_report() -> dict[str, str]:
    """Collect environment facts without touching secrets or hardware."""
    return {
        "status": "ok",
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def make_sample_wav(path: str, seconds: int = 10, rate: int = SAMPLE_RATE) -> str:
    """Write silence as 16-bit mono WAV. No microphone, no user data."""
    frames = b"\x00\x00" * (rate * seconds)
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)
    return path


def build_sample_result(claim: ClaimResponse, elapsed: float) -> dict:
    """Sample WorkerResult body: 2 segments, speakers only when diarized."""
    diarized = claim.diarization
    duration = 60.0
    segments = [
        {
            "index": i,
            "start": start,
            "end": end,
            "text": text,
            "confidence": conf,
            "speaker_id": spk if diarized else None,
            "edited": False,
            "version": 1,
        }
        for i, (start, end, text, spk, conf) in enumerate(SAMPLE_LINES)
    ]
    return {
        "segments": segments,
        "speakers": SAMPLE_SPEAKERS if diarized else [],
        "diarization_available": diarized,
        "duration_seconds": duration,
        "xrt": duration / max(elapsed, 0.1),
        "model_version": "fake-0.1.0",
        "low_confidence_ratio": 0.0,
    }


def run_fake_once(client: httpx.Client, wait: int = 25,
                  process_seconds: float = 3.0) -> str | None:
    """Claim one job, fake-process it, submit the result. Returns job_id."""
    resp = client.post("/worker/v1/jobs/claim", params={"wait": wait})
    if resp.status_code == 204:
        print("fake worker: antrean kosong")
        return None
    resp.raise_for_status()
    claim = ClaimResponse.model_validate(resp.json())
    print(f"fake worker: claimed {claim.job_id} "
          f"(diarisasi={'ya' if claim.diarization else 'tidak'})")

    started = time.monotonic()
    for stage in (ProcessingStage.PROBING, ProcessingStage.TRANSCRIBING):
        client.post(f"/worker/v1/jobs/{claim.job_id}/heartbeat",
                    json={"stage": stage}).raise_for_status()
        time.sleep(process_seconds / 3.0)
    if claim.diarization:
        client.post(f"/worker/v1/jobs/{claim.job_id}/heartbeat",
                    json={"stage": ProcessingStage.DIARIZING}).raise_for_status()
        time.sleep(process_seconds / 3.0)

    result = build_sample_result(claim, time.monotonic() - started)
    client.post(f"/worker/v1/jobs/{claim.job_id}/result",
                json=result).raise_for_status()
    print(f"fake worker: selesai {claim.job_id} (xrt={result['xrt']:.1f})")
    return str(claim.job_id)


def run_fake_loop(api_url: str, once: bool) -> int:
    with httpx.Client(base_url=api_url, timeout=60.0) as client:
        try:
            ping = client.post("/worker/v1/ping",
                               json={"worker_id": "fake-local",
                                     "version": "0.1.0"}).json()
        except httpx.ConnectError:
            print(f"fake worker: tidak bisa hubungi {api_url}. "
                  "Jalankan `make dev-up` dulu.")
            return 1
        if ping.get("update_required"):
            print("fake worker: versi ditolak, perbarui dulu.")
            return 1
        while True:
            run_fake_once(client)
            if once:
                return 0
            time.sleep(2.0)


def demo(api_url: str) -> int:
    """Seed one dev job on the TK-002 fake API and complete it end to end."""
    with httpx.Client(base_url=api_url, timeout=60.0) as client:
        try:
            seed = client.post("/dev/jobs", json={"language": "id",
                                                  "diarization": True}).json()
        except httpx.ConnectError:
            print(f"demo: tidak bisa hubungi {api_url}. Jalankan `make dev-up` dulu.")
            return 1
        job_id = seed["job_id"]
        print(f"demo: job {job_id} dibuat (queued)")
        run_fake_once(client, wait=5)
        transcript = client.get(f"/api/jobs/{job_id}/transcript").json()
        print(f"demo: {len(transcript['segments'])} segmen, "
              f"{len(transcript['speakers'])} pembicara")
        for seg in transcript["segments"]:
            print(f"  [{seg['start']:.1f}-{seg['end']:.1f}] "
                  f"({seg['speaker_id']}) {seg['text']}")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worker", description="BeosaBasi worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check worker environment (stub, TK-005)")
    sample = sub.add_parser("make-sample", help="Write a silent WAV fixture")
    sample.add_argument("--out", default="contoh-hening-10s.wav")
    sample.add_argument("--seconds", type=int, default=10)
    run = sub.add_parser("run", help="Run the worker loop")
    run.add_argument("--fake", action="store_true",
                     help="Fake mode: sample output, no GPU (TK-002)")
    run.add_argument("--api-url", default=DEFAULT_API_URL)
    run.add_argument("--once", action="store_true",
                     help="Process a single job then exit")
    demo_p = sub.add_parser("demo", help="Seed + complete one job (TK-002 fake API)")
    demo_p.add_argument("--api-url", default=DEFAULT_API_URL)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        # TODO(TK-005): GPU/VRAM, CUDA/cuDNN, ffmpeg/ffprobe, workdir,
        # HF token presence (never print), sleep guard, battery/thermal.
        report = doctor_report()
        print(f"worker doctor: {report['status']} "
              f"(python={report['python']}, platform={report['platform']})")
        print("TODO(TK-005): full hardware checks not implemented yet")
        return 0
    if args.command == "make-sample":
        path = make_sample_wav(args.out, seconds=args.seconds)
        print(f"sample written: {path} ({args.seconds}s silence, {SAMPLE_RATE} Hz)")
        return 0
    if args.command == "run":
        if not args.fake:
            print("real GPU loop arrives in TK-030; use `run --fake` for now.")
            return 2
        try:
            return run_fake_loop(args.api_url, args.once)
        except KeyboardInterrupt:
            print("fake worker: dihentikan.")
            return 0
    if args.command == "demo":
        return demo(args.api_url)
    return 1


if __name__ == "__main__":
    sys.exit(main())
