"""Minimal FastAPI scaffold. Real routes arrive in TK-021+."""

import os

from fastapi import FastAPI

from api.health import health_status

app = FastAPI(title="BeosaBasi API", version="0.1.0")

if os.getenv("BEOSABASI_FAKE") == "1":
    # DEV ONLY (TK-002): in-memory fake backend, no R2/GPU/auth. Real
    # routers from TK-020+ replace these paths. Never enable in production.
    from api.fake import router as fake_router

    app.include_router(fake_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return health_status()
