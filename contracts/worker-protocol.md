# Protokol Pekerja BeosaBasi (TK-001)

Pekerja di laptop (Windows, Python) hanya membuat koneksi HTTPS **keluar** ke VPS.
Tidak ada port masuk. Autentikasi memakai header
`Authorization: Bearer <token pekerja>` (token acak 256-bit, hanya hash yang
disimpan di VPS, dapat dirotasi). Skema JSON-validated ada di
`contracts/openapi.yaml` (`/worker/v1/...`, komponen `ClaimResponse`,
`Heartbeat`, `WorkerResult`, `WorkerFail`, `WorkerPing`).

## Alur hidup satu job

```
claim → heartbeat (tiap 30 dtk) → result | fail
```

1. `POST /worker/v1/jobs/claim?wait=25`. VPS menahan hingga 25 detik bila
   antrean kosong. Respons `200` berisi `job_id`, `audio_url` (URL GET R2
   bertanda tangan, TTL 15 menit), pengaturan bahasa/diarisasi, dan
   `lease_until` (sewa 5 menit). Respons `204` berarti antrean kosong.
   Pengambilan bersifat atomik: satu job hanya untuk satu pekerja (PRD 4.7).
2. Pekerja mengunduh audio ke direktori kerja sementara, menjalankan
   `ffprobe`/`ffmpeg` (AI-01, AI-02), lalu tahap pemrosesan sesuai `stage`:
   `probing → transcribing → (diarizing) → merging` (PRD 4.5, 4.8).
3. `POST /worker/v1/jobs/{id}/heartbeat` tiap 30 detik dengan `stage` dan
   `progress_percent`. VPS memperpanjang sewa dan dapat membalas
   `cancel: true` bila pengguna menghapus job — pekerja wajib berhenti dan
   menghapus berkas kerja.
4. Sewa kedaluwarsa (tanpa detak > 5 menit) mengembalikan job ke antrean,
   `attempts + 1`, maksimal 3 lalu `failed` (AI-09).
5. `POST /worker/v1/jobs/{id}/result` berisi segmen (mulai/selesai/teks/
   keyakinan/speaker), pembicara, durasi, `xrt`, `model_version`, dan
   `low_confidence_ratio`. Bila diarisasi gagal, kirim hasil **tanpa label**
   dengan `diarization_available: false` (kuota tambahan dikembalikan, AI-13).
6. `POST /worker/v1/jobs/{id}/fail` berisi `code` + `retryable`. Galat CUDA OOM
   dicoba ulang sekali dengan batch setengah sebelum `failed` (AI-07).
7. `POST /worker/v1/ping` saat start: `{worker_id, version}`. VPS menolak versi
   yang terlalu lama (`update_required: true`).

## Kode galat (`KodeGalat`) dan pesan manusiawi

| Kode | Arti | Pesan untuk pengguna (id) |
|---|---|---|
| `INVALID_FILE` | Berkas bukan audio/video yang dikenal | Berkas tidak dikenali. Unggah MP3, M4A, WAV, FLAC, OGG/Opus, MP4, atau WebM. |
| `UNSUPPORTED_TYPE` | Tipe konten di luar daftar US-01 | Tipe berkas belum didukung. |
| `TOO_LARGE` | Melebihi 200 MB | Berkas melebihi 200 MB. |
| `TOO_LONG` | Melebihi 90 menit | Audio melebihi 90 menit. |
| `NO_AUDIO_STREAM` | Kontainer tanpa aliran audio | Berkas tidak berisi audio. |
| `CORRUPT_MEDIA` | `ffprobe`/`ffmpeg` gagal | Berkas rusak dan tidak bisa diproses. Coba ekspor ulang. |
| `QUOTA_EXCEEDED` | Kuota harian habis | Kuota hari ini habis. Coba lagi setelah tengah malam WIB. |
| `TOO_MANY_ACTIVE_JOBS` | > 2 job aktif | Maksimal 2 pekerjaan bersamaan. Tunggu satu selesai dulu. |
| `CONSENT_REQUIRED` | Belum ada persetujuan tercatat | Beri persetujuan privasi dulu sebelum mengunggah. |
| `ALLOWLIST_REQUIRED` | Email di luar daftar undangan | Akun belum terdaftar di pilot tertutup. |
| `WORKER_OFFLINE` | Pekerja tidak berdetak > 90 dtk | Pemrosesan tertunda karena perangkat mati. Job aman dan jalan otomatis saat perangkat aktif. |
| `LEASE_LOST` | Sewa diambil alih / job dibatalkan | Pekerjaan dihentikan karena dibatalkan. |
| `GPU_OOM` | VRAM habis (2x gagal) | Perangkat kehabisan memori GPU. Coba berkas lebih pendek. |
| `DIARIZATION_FAILED` | Tahap diarisasi gagal | Label pembicara tidak tersedia, transkrip tetap diberikan. Kuota tambahan dikembalikan. |
| `FFMPEG_ERROR` | Konversi audio gagal | Gagal menyiapkan audio. Coba format lain. |
| `JOB_TIMEOUT` | `ffmpeg` > 10 menit / proses macet | Pemrosesan terlalu lama dan dihentikan. |
| `JOB_EXPIRED` | Menunggu pekerja > 72 jam | Pekerjaan kedaluwarsa karena perangkat lama mati. Unggah ulang. |
| `VERSION_CONFLICT` | Suntingan bertabrakan | Segmen diubah di tempat lain. Muat ulang lalu sunting lagi. |
| `AUDIO_GONE` | Audio lewat retensi 24 jam | Audio sudah dihapus sesuai kebijakan retensi. Transkrip tetap bisa disunting. |
| `INTERNAL` | Galat tak terduga | Terjadi galat. Coba lagi, lapor bila berulang. |

## Aturan higiene data pekerja (AI-10)

Berkas kerja dihapus di blok `finally` apa pun hasilnya. Log pekerja tidak
memuat teks transkrip maupun nama berkas pengguna. Audio dan teks pengguna
tidak dikirim ke layanan AI pihak ketiga dan tidak dipakai melatih model.
Token Hugging Face (untuk unduh model diarisasi) hanya di variabel lingkungan.

## Perubahan kontrak

Perubahan file ini atau `openapi.yaml` wajib lewat PR yang menandai jalur
terdampak (`API`, `WRK`, `WEB`) dan menjalankan ulang `make gen-client`.
