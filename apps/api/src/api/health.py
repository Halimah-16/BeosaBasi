"""Health helper kept free of FastAPI imports so unit tests stay light."""


def health_status() -> dict[str, str]:
    return {"status": "ok"}
