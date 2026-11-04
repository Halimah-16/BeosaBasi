# Development image: fake backend enabled, no secrets, no GPU.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/api/src \
    BEOSABASI_FAKE=1

WORKDIR /srv/api
COPY pyproject.toml ./
RUN pip install --no-cache-dir "fastapi>=0.115,<0.117" "pydantic>=2.9,<3" "uvicorn>=0.30,<0.35" "httpx>=0.27,<1"
COPY src ./src
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
