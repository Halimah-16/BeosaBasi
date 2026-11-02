# BeosaBasi

Layanan web gratis untuk individu: pengguna mengunggah berkas audio/video lalu
menerima transkrip bahasa Indonesia berpenanda waktu yang bisa disunting dan
diekspor. Inferensi memakai Whisper large-v3-turbo di laptop pengelola
(RTX 4050); web statis di Cloudflare Pages; API + antrean di VPS; audio
sementara di Cloudflare R2. Lihat `docs/PRD.md` (v1.0) dan `docs/TICKETS.md`.

> Status: scaffold repositori (TK-000). Endpoint, pekerja, dan benchmark nyata
> dikerjakan di tiket berikutnya.

## Arsitektur (PRD 4.1)

```
 Browser pengguna
   |  (1) HTML/JS statis                 (2) API JSON (HTTPS)          (3) PUT potongan audio
   v                                      v                             v
 Cloudflare Pages  <--- DNS/WAF/Turnstile --->  VPS (2 vCPU, 2 GB)     Cloudflare R2 (privat)
 app.<domain>                                  api.<domain>            endpoint S3, URL bertanda tangan
                                               Caddy -> FastAPI           ^         ^
                                               SQLite (WAL) + penjadwal   |         |
                                                  ^                       |         |
                                                  | (4) HTTPS keluar      |         |
                                                  |  claim/heartbeat/hasil| (5) GET audio (URL bertanda tangan)
                                                  |                       |         |
                                         Laptop RTX 4050 (Windows) -------+---------+
                                         pekerja Python: ffmpeg, Whisper, pyannote
                                         tanpa port masuk
```

## Struktur repo (PRD 4.2/4.3)

| Path | Isi |
|---|---|
| `apps/web/` | Vite + React + TypeScript (Cloudflare Pages) |
| `apps/api/` | FastAPI, migrasi SQLite, penjadwal retensi |
| `apps/worker/` | Pekerja inferensi (Windows), CLI benchmark |
| `contracts/` | `openapi.yaml`, skema/protokol pekerja (penuh di TK-001) |
| `eval/` | Set uji (di luar git bila berisi suara), skrip WER/DER, hasil per versi |
| `infra/` | Caddy, compose/systemd, CORS dan lifecycle R2 |
| `docs/` | PRD, TICKETS, ADR, privasi, runbook |

## Cara menjalankan lokal

Prasyarat: Python 3.12 (`uv` disarankan), Node 20+.

```bash
make setup   # install deps python + npm
make lint    # ruff (api, worker) + eslint (web)
make test    # pytest (api, worker) + vitest (web)
```

Dev server per aplikasi (`make dev-api`, `make dev-web`, `make dev-worker`)
dan `make gen-client` masih stub TODO sampai TK-001/TK-002 selesai.

## Peta tiket

| Fase | Tiket | Keterangan |
|---|---|---|
| 0 Scaffold | TK-000 (ini), TK-001, TK-002 | Fondasi; setelah TK-001 jalur paralel |
| 0 Infra/benchmark | TK-003, TK-004, TK-005, TK-010..TK-014, TK-050 | INF + EVAL |
| 1 MVP | TK-020..TK-029 (API), TK-030..TK-035 (WRK), TK-040..TK-045 (WEB), TK-060..TK-063 | Pilot tertutup |
| 2 Diarisasi | TK-051..TK-054, TK-046 | Bergantung TK-050 |
| 3 Opsional | TK-070 | Perluasan, perlu telaah hukum |

Detail: `docs/TICKETS.md`. Keputusan teknologi: PRD 4.2 (`docs/PRD.md`).
