"""Minimal FastAPI scaffold. Full routes arrive in TK-021+."""

from fastapi import FastAPI

from api.health import health_status

app = FastAPI(title="BeosaBasi API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return health_status()
