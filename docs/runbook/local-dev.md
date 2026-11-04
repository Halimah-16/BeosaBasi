# Pengembangan lokal (TK-002)

Tanpa akun Cloudflare, tanpa GPU, tanpa R2 asli. Stack lokal memakai API
dengan backend palsu dalam memori (`BEOSABASI_FAKE=1`) dan Garage sebagai
pengganti R2 yang kompatibel S3 (mendukung multipart upload seperti R2).

## Prasyarat

Docker Desktop (untuk `dev-up`), Python 3.12 + `uv`, Node 20 + npm.

## Alur 5 menit

```powershell
make dev-up
```

API sehat di `http://localhost:8000` (`/healthz` menjawab `{"status":"ok"}`).
Garage (S3 lokal) di `http://localhost:3900`, admin di `http://localhost:3903`.
Kredensial dev dicetak oleh `dev-up`: region `garage`, bucket `beosabasi-dev`.
Semua kredensial ini hanya untuk laptop dan tidak dipakai di produksi.

Jalankan satu job ujung ke ujung dengan pekerja palsu:

```powershell
cd apps/worker
uv run worker demo
```

`demo` membuat satu job lewat `POST /dev/jobs`, menyelesaikannya lewat
`claim → heartbeat → result`, lalu mencetak 2 segmen contoh. Tanpa GPU:
pekerja hanya tidur 3 detik sebagai pengganti inferensi.

Mode loop (2+ job, `--once` untuk satu job):

```powershell
uv run worker run --fake
uv run worker run --fake --once
```

Fixture audio hening 10 detik (dibuat saat dibutuhkan, tidak dikomit karena
`*.wav` diabaikan git):

```powershell
uv run worker make-sample --out contoh-hening-10s.wav
```

Hentikan stack:

```powershell
make dev-down
```

## Mock API untuk pengembangan web

Kontrak OpenAPI dipakai sebagai server tiruan agar `web` bisa jalan tanpa API:

```powershell
cd apps/web
npm run mock:api   # Prism di http://localhost:4010 dari contracts/openapi.yaml
```

Contoh respons buatan ada di `contracts/mock/fixtures.json`.

## Regenerasi klien dari kontrak

Setiap perubahan `contracts/openapi.yaml` wajib diikuti:

```powershell
python scripts/gen_client.py  # atau: make gen-client
```

CI menolak PR bila file terhasilkan (`api-types.ts`, kedua `schemas.py`)
tidak sinkron dengan kontrak.

## Pemecahan masalah

| Gejala | Periksa |
|---|---|
| `dev-up` gagal: Docker tidak tersedia | Nyalakan Docker Desktop, ulangi |
| API tidak menjawab `/healthz` | `docker compose -f infra/compose.local.yaml logs api` |
| `demo` gagal koneksi | Pastikan `make dev-up` hijau dulu |
| Port 8000/3900 dipakai | Hentikan layanan lain atau ubah port di `infra/compose.local.yaml` |
| `gen-client` gagal: pyyaml hilang | Skrip memasang `pyyaml` otomatis; butuh jaringan sekali |
