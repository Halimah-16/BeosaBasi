# Keterlacakan US → Endpoint (TK-001)

Setiap user story di PRD 2.3 punya endpoint yang jelas di
`contracts/openapi.yaml`. Tabel ini yang membuat jalur `API`, `WRK`, dan `WEB`
bisa paralel setelah TK-001.

| US | Endpoint |
|---|---|
| US-01 unggah + transkripsi | `POST /api/uploads`, `POST /api/uploads/{id}/parts`, `GET /api/uploads/{id}`, `POST /api/uploads/{id}/complete`, `GET /api/jobs/{id}` |
| US-02 status job | `GET /api/jobs`, `GET /api/jobs/{id}` (posisi antrean, ETA, `worker_active`) |
| US-03 sunting tersinkron | `GET /api/jobs/{id}/transcript`, `PATCH /api/jobs/{id}/segments/{n}`, `GET /api/jobs/{id}/audio-url` |
| US-04 ekspor | `GET /api/jobs/{id}/export?format=txt\|srt\|vtt\|docx` |
| US-05 hapus data | `DELETE /api/jobs/{id}`, `DELETE /api/me` |
| US-06 persetujuan + privasi | `POST /api/consents`, `DELETE /api/consents`, `GET /api/me` (status persetujuan) |
| US-07 kuota | `GET /api/me` (`quota_minutes_remaining`, `active_jobs`), `POST /api/uploads` (penolakan kuota) |
| US-08 pelabelan pembicara | `POST /api/uploads` (`diarization`, `min/max_speakers`), `GET /api/jobs/{id}/transcript`, `PATCH /api/jobs/{id}/speakers/{sid}`, `PATCH /api/jobs/{id}/segments/{n}` (pindah pembicara), ekspor memakai nama |
| Pekerja (semua US) | `POST /worker/v1/jobs/claim`, `POST /worker/v1/jobs/{id}/heartbeat`, `POST /worker/v1/jobs/{id}/result`, `POST /worker/v1/jobs/{id}/fail`, `POST /worker/v1/ping` |
| Auth + sesi | `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/logout` |
| Observabilitas | `GET /healthz` |

Aturan perubahan: ubahan kontrak lewat PR berlabel jalur terdampak dan
menjalankan ulang `make gen-client` agar `api-types.ts` dan kedua
`schemas.py` tetap sinkron.
