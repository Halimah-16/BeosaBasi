# TICKETS: Layanan Transkripsi Suara-ke-Teks (Whisper large-v3-turbo)

Pecahan pekerjaan dari `PRD.md` v1.0. Dimulai dari scaffold. Tanpa tenggat (D-19). Urutan ditentukan oleh dependensi dan kriteria keluar fase, bukan tanggal.

**Cara membaca**

- **Jalur (track):** `INF` infrastruktur, `API` VPS, `WRK` pekerja laptop, `WEB` antarmuka, `EVAL` benchmark dan set uji, `SPK` pelabelan pembicara, `DOC` hukum dan dokumen, `QA` pengujian.
- **Ukuran:** S ≤ setengah hari, M 1 sampai 2 hari, L 3 sampai 5 hari. Ukuran relatif, bukan janji.
- **Tipe:** `kode`, `manual` (dikerjakan manusia di dasbor atau di dunia nyata), `riset` (spike dengan keluaran berupa keputusan).
- **Rujukan:** nomor bagian PRD, ID persyaratan (US, AI, K), keputusan (D), pertanyaan terbuka (T).
- Tiket yang bertanda **GERBANG** menghasilkan keputusan yang harus dicatat di PRD Lampiran A sebelum tiket turunannya dimulai.

---

## Ringkasan dan Urutan

| Fase | Tiket | Keterangan |
|---|---|---|
| **0 Scaffold** | TK-000, TK-001, TK-002 | Wajib lebih dulu. Setelah TK-001 selesai, jalur lain bisa paralel. |
| **0 Infra dan benchmark** | TK-003, TK-004, TK-005, TK-010 sampai TK-014, TK-050 | Jalur `INF` dan `EVAL` berjalan paralel dengan jalur `API` dan `WEB` |
| **1 MVP** | TK-020 sampai TK-029, TK-030 sampai TK-035, TK-040 sampai TK-045, TK-060, TK-061, TK-062, TK-063 | Pilot tertutup |
| **2 Pelabelan pembicara** | TK-051 sampai TK-054, TK-046 | Bergantung pada TK-050 dan pekerja MVP |
| **3 Opsional** | TK-070 | Pendaftaran lebih terbuka dan lintas rekaman, perlu telaah hukum |

### Graf Dependensi Ringkas

```
TK-000 ──> TK-001 ──┬─> TK-020 ─> TK-021 ─> TK-022 ─> TK-023 ─> TK-024 ─> TK-025 ─> TK-026 ─> TK-027
   │                │                                                 │
   │                ├─> TK-030 ─> TK-031 ─> TK-032 ─> TK-033 ─> TK-034/035
   │                ├─> TK-040 ─> TK-041 ─> TK-042 ─> TK-043 ─> TK-044 ─> TK-045
   │                └─> TK-002
   ├─> TK-005 ─> TK-010 ─> TK-012 ─> TK-013 (GERBANG model) ──> TK-032 (parameter final)
   └─> TK-003, TK-004          TK-011 (set uji) ─┘
TK-005 ─> TK-050 (GERBANG diarisasi) ─> TK-051 ─> TK-052 ─> TK-054, TK-053 ─> TK-046
```

### Jalur Paralel yang Disarankan (bila dikerjakan beberapa orang atau beberapa agen)

| Jalur | Tiket pertama setelah TK-001 | Tidak saling memblokir dengan |
|---|---|---|
| A `API` (VPS) | TK-020 | WEB, WRK, EVAL |
| B `WRK` (laptop) | TK-030 (memakai pekerja palsu di TK-002 untuk uji ujung ke ujung) | API, WEB |
| C `WEB` | TK-040 (memakai server tiruan dari kontrak) | API, WRK |
| D `EVAL` | TK-010, TK-011 | semua jalur lain |
| E `INF` dan `DOC` | TK-003, TK-004, TK-005, TK-060 | semua jalur lain |

---

## Fase 0: Scaffold

### TK-000: Scaffold repositori monorepo
- **Jalur / ukuran / tipe:** INF / M / kode
- **Dependensi:** tidak ada
- **Rujukan:** PRD 4.3, 4.2
- **Deskripsi:** Buat struktur repositori sesuai 4.3 beserta perkakas dasar agar semua jalur punya fondasi yang sama.
- **Pekerjaan:**
  - Struktur: `apps/web`, `apps/api`, `apps/worker`, `contracts`, `eval`, `infra`, `docs`.
  - Salin `PRD.md` dan `TICKETS.md` ke `docs/` dan akar repo. Tambahkan `docs/ADR/` dengan templat ADR dan `docs/runbook/` kosong.
  - Python: `uv` atau `pip-tools` dengan versi Python dipatok di `.python-version`. `ruff`, `pytest`, `mypy` (opsional) untuk `apps/api` dan `apps/worker`. Satu `pyproject.toml` per aplikasi.
  - Web: `pnpm` (atau `npm`), Vite + React + TypeScript, `eslint`, `vitest`.
  - `Makefile` atau `justfile` dengan target: `setup`, `lint`, `test`, `dev-api`, `dev-web`, `dev-worker`, `gen-client`.
  - `.gitignore` (termasuk `eval/data/`, `*.wav`, `*.mp3`, `.env`, `*.db`), `.env.example` per aplikasi tanpa nilai rahasia, `.editorconfig`, `pre-commit` (ruff, eslint, deteksi rahasia seperti `gitleaks`).
  - CI (GitHub Actions): lint dan uji untuk `api`, `worker`, `web`. Tidak ada rahasia di CI.
  - `README.md`: tujuan, diagram arsitektur 4.1, cara menjalankan lokal, peta tiket.
  - `LICENSE` dan `NOTICE` dengan atribusi model (R-12): Whisper, pyannote community-1 (CC-BY-4.0).
- **Kriteria penerimaan:**
  - `make setup && make lint && make test` lulus di mesin bersih (Windows untuk `worker`, Linux atau Windows untuk `api` dan `web`).
  - Setiap aplikasi punya satu uji dummy yang dijalankan CI.
  - Pemindaian rahasia aktif dan memblokir commit yang berisi kunci contoh.
  - Tidak ada berkas audio atau data pengguna di repo.

### TK-001: Kontrak API dan protokol pekerja
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-000
- **Rujukan:** PRD 4.4 sampai 4.7, 4.5, AI-06
- **Deskripsi:** Tulis `contracts/openapi.yaml` untuk API pengguna dan `contracts/worker-protocol.md` (atau skema JSON) untuk API pekerja. Ini kontrak yang membuat jalur `API`, `WRK`, dan `WEB` bisa paralel.
- **Pekerjaan:**
  - Skema semua endpoint di 4.7 (jalur, metode, badan, respons, kode galat standar).
  - Enumerasi status job dan tahap pemrosesan (4.5). Daftar `kode_galat` dan pesan manusiawi (Indonesia).
  - Skema hasil pekerja: segmen (mulai, selesai, teks, keyakinan, speaker), pembicara, metadata (xRT, versi model, rasio keyakinan rendah).
  - Skrip `make gen-client` yang menghasilkan tipe TypeScript untuk `web` dan model Pydantic untuk `api` dan `worker`.
  - Server tiruan (Prism atau sejenis) untuk pengembangan `web` tanpa API nyata.
- **Kriteria penerimaan:**
  - OpenAPI lolos validator. Klien TS dan model Python terhasilkan tanpa galat.
  - Setiap persyaratan US-01 sampai US-08 punya endpoint yang jelas di kontrak (tabel keterlacakan di `docs/`).
  - Perubahan kontrak setelah tiket ini wajib lewat PR yang menandai jalur terdampak.

### TK-002: Lingkungan lokal dan pekerja palsu
- **Jalur / ukuran / tipe:** INF / M / kode
- **Dependensi:** TK-000, TK-001
- **Rujukan:** PRD 4.1, 4.6
- **Deskripsi:** Agar pengembangan tidak bergantung pada R2, GPU, dan Cloudflare.
- **Pekerjaan:**
  - `docker compose` lokal: API, MinIO (pengganti R2 yang kompatibel S3), satu kontainer untuk SQLite volume.
  - `apps/worker` mode `--fake`: mengambil job, menunggu beberapa detik, mengirim transkrip contoh dan pembicara contoh. Tanpa GPU.
  - Data contoh: satu audio hening 10 detik buatan sendiri (bukan data pengguna).
  - Panduan `docs/runbook/local-dev.md`.
- **Kriteria penerimaan:**
  - `make dev-up` menjalankan API + MinIO, dan pekerja palsu dapat menyelesaikan satu job buatan lewat HTTP.
  - Tidak membutuhkan akun Cloudflare maupun GPU.

---

## Fase 0: Infrastruktur dan Benchmark

### TK-003: Pengaturan Cloudflare (Pages, R2, DNS, Turnstile)
- **Jalur / ukuran / tipe:** INF / M / manual
- **Dependensi:** TK-000, T-14 (nama dan domain)
- **Rujukan:** PRD 4.1, 4.6, 4.9, 4.11, D-13
- **Pekerjaan:**
  - Domain dan DNS. `app.<domain>` untuk Pages, `api.<domain>` untuk VPS dengan proksi aktif.
  - Proyek Pages terhubung ke repo (`apps/web`).
  - Bucket R2 privat. Pilih petunjuk lokasi dan catat konsekuensi lintas negara di `docs/privasi/`.
  - CORS bucket: asal `https://app.<domain>`, metode `GET`, `PUT`, header `Content-Type`, `ExposeHeaders: ETag`.
  - Aturan siklus hidup: batalkan multipart menggantung (1 hari), hapus objek `uploads/` > 7 hari.
  - Token API R2 dengan izin sesempit mungkin (khusus bucket). Situs Turnstile (kunci situs dan kunci rahasia).
  - Baca penuh Service-Specific Terms Cloudflare untuk R2 dan penyajian audio (T-13). Catat hasil di `docs/`.
  - Simpan konfigurasi sebagai berkas di `infra/cloudflare/` (CORS JSON, lifecycle JSON, wrangler untuk Pages).
- **Kriteria penerimaan:**
  - Unggah dan unduh berkas uji kecil lewat URL bertanda tangan dari peramban di asal Pages berhasil, tanpa galat CORS.
  - Objek uji terhapus otomatis oleh aturan siklus hidup (diverifikasi, atau diset pendek sementara untuk pengujian).
  - Tidak ada kredensial di repo.

### TK-004: Penyiapan VPS
- **Jalur / ukuran / tipe:** INF / M / manual + kode
- **Dependensi:** TK-000, TK-003
- **Rujukan:** PRD 4.1, 4.9, 4.13, 4.15, R-10
- **Pekerjaan:**
  - Pengerasan dasar: pengguna non-root, SSH kunci saja, pembaruan keamanan otomatis, firewall (HTTPS hanya dari rentang IP Cloudflare, SSH dari IP pengelola).
  - Swap 1 GB. Pemantauan RAM dan disk dengan ambang 80%.
  - Caddy sebagai proksi balik ke FastAPI. Autentikasi asal (Authenticated Origin Pulls) bila praktis.
  - Compose atau systemd (putuskan dengan ADR). Mulai otomatis saat reboot.
  - Cadangan SQLite harian (`sqlite3 .backup`), terenkripsi, simpan 7 hari, di luar disk utama.
  - `make deploy` terskrip dan prosedur rollback di `docs/runbook/deploy.md`.
  - Pemantau waktu aktif eksternal untuk `GET /healthz`.
- **Kriteria penerimaan:**
  - `curl https://api.<domain>/healthz` berhasil lewat Cloudflare. Akses langsung ke IP VPS ditolak.
  - Reboot VPS memulihkan layanan tanpa tindakan manual.
  - Pemulihan dari cadangan dicoba sekali dan dicatat.

### TK-005: Penyiapan laptop Windows dan perintah `doctor`
- **Jalur / ukuran / tipe:** WRK / M / manual + kode
- **Dependensi:** TK-000
- **Rujukan:** PRD 3.1, 3.3, AI-08, D-16, T-07, T-11
- **Pekerjaan:**
  - Akun Windows khusus pekerja tanpa hak admin. Direktori kerja dengan izin terbatas.
  - Pasang driver NVIDIA, CUDA, cuDNN, Python, PyTorch CUDA, `faster-whisper`, `ffmpeg`. Catat kombinasi versi yang lolos.
  - Perintah `worker doctor` yang memeriksa: GPU terdeteksi dan VRAM bebas, CUDA dan cuDNN dapat dimuat oleh CTranslate2 dan PyTorch, `ffmpeg` dan `ffprobe` ada dan versinya, direktori kerja dapat ditulis, token Hugging Face ada (tanpa mencetaknya), pencegah tidur berfungsi, status baterai dan suhu terbaca.
  - Task Scheduler (atau NSSM) untuk menjalankan pekerja saat masuk. Pengaturan daya untuk mencegah tidur selama job.
  - `docs/runbook/worker-windows.md` dengan langkah pemasangan dan versi terkunci (`requirements.lock`).
  - Bila `faster-whisper` dan `pyannote` tidak bisa berdampingan di Windows asli, dokumentasikan jalur WSL2 sebagai gantinya dan catat keputusan (D-16 diperbarui).
- **Kriteria penerimaan:**
  - `worker doctor` mencetak laporan lulus semua pemeriksaan di laptop target.
  - Satu transkripsi uji (audio contoh buatan sendiri) berjalan di GPU lewat skrip pendek.
  - Versi terkunci tercatat di repo.

### TK-010: Harness benchmark transkripsi
- **Jalur / ukuran / tipe:** EVAL / M / kode
- **Dependensi:** TK-005
- **Rujukan:** PRD 3.4.4, K2
- **Pekerjaan:**
  - CLI `worker bench <folder>` yang menjalankan pipeline transkripsi pada folder audio dan menulis JSON per klip: durasi, waktu proses, xRT, VRAM puncak, suhu GPU, jumlah segmen, versi model dan pustaka.
  - Opsi untuk membandingkan: `int8_float16` vs `float16`, `beam_size`, batch, VAD on/off, turbo vs large-v3 int8.
  - Pengukuran waktu muat model terpisah dari waktu inferensi.
  - Pengulangan 3 kali untuk file 60 menit dengan median dan terburuk.
- **Kriteria penerimaan:**
  - Menghasilkan laporan xRT dan VRAM puncak yang dapat dibandingkan antar konfigurasi.
  - Hasil tersimpan di `eval/results/<versi>/` dalam bentuk JSON.

### TK-011: Set uji 60 klip dan pedoman anotasi
- **Jalur / ukuran / tipe:** EVAL / L / manual
- **Dependensi:** tidak ada (dapat dimulai segera, jalur manusia)
- **Rujukan:** PRD 3.4.1, 3.4.2, K1
- **Pekerjaan:**
  - Kumpulkan 60 klip × 1 menit (5 kategori × 12): wawancara, rapat, pesan suara WhatsApp, audio berderau, campur Indonesia-Inggris. Rekaman sendiri dengan persetujuan tertulis semua pembicara (formulir persetujuan di `docs/`).
  - Tambah 20 klip hening atau derau murni untuk uji halusinasi.
  - Tulis pedoman anotasi (ejaan baku vs informal, kata pengisi, angka, nama, kata serapan).
  - Anotasi oleh 2 penyunting independen. Hitung WER antar-penyunting. Bila > 5%, perbaiki pedoman, anotasi ulang, rekonsiliasi.
  - Bekukan set uji (hash berkas, versi) sebelum benchmark. Data suara tidak masuk git. Simpan di folder terenkripsi atau penyimpanan pribadi, dengan indeks dan hash di `eval/`.
- **Kriteria penerimaan:**
  - 60 klip bertranskrip acuan terekonsiliasi dan 20 klip hening tersedia. Hash set uji tercatat.
  - Setiap pembicara punya persetujuan tertulis yang tersimpan terpisah dari audio.

### TK-012: Pipeline skor WER dan daftar pemetaan
- **Jalur / ukuran / tipe:** EVAL / M / kode
- **Dependensi:** TK-010, TK-011
- **Rujukan:** PRD 3.4.3, 3.4.4, D-12
- **Pekerjaan:**
  - Normalisasi (huruf kecil, tanda baca, kata pengisi) dan WER ketat vs WER longgar dengan `jiwer`.
  - Daftar pemetaan varian ejaan (versi, dibekukan sebelum uji). Uji unit untuk normalisasi.
  - Laporan per kategori, keseluruhan, dan metrik halusinasi, pengulangan, ketepatan waktu (daftar sampel 100 segmen untuk pemeriksaan manual).
- **Kriteria penerimaan:**
  - Satu perintah menghasilkan laporan Markdown dan JSON dari hasil benchmark.
  - Daftar pemetaan berversi dan tidak berubah setelah hasil pertama dilihat (dicek oleh hash di CI).

### TK-013: Jalankan benchmark dan keputusan model (GERBANG)
- **Jalur / ukuran / tipe:** EVAL / M / riset
- **Dependensi:** TK-010, TK-011, TK-012
- **Rujukan:** PRD 3.4.4, 3.4.5, 3.4.8, K1, K2
- **Pekerjaan:**
  - Jalankan benchmark turbo dan large-v3 int8 pada set uji dan pada file 60 menit.
  - Isi tabel metrik di 3.4.4 dengan angka nyata. Hitung kapasitas harian (3.4.5) dan kuota yang masuk akal.
  - Terapkan pintu keputusan 3.4.8. Perbarui PRD: nilai [T] menjadi nilai terukur, Lampiran A (keputusan baru), kuota di 2.4.
- **Kriteria penerimaan:**
  - Laporan `eval/results/<versi>/report.md` lengkap. Keputusan model tercatat di Lampiran A.
  - xRT, VRAM puncak, kebutuhan waktu muat, dan WER longgar per kategori dilaporkan.

### TK-014: Uji halusinasi, pengulangan, dan penanda waktu
- **Jalur / ukuran / tipe:** EVAL / M / kode + manual
- **Dependensi:** TK-012
- **Rujukan:** PRD AI-03, AI-05, 3.4.4
- **Pekerjaan:** Kalibrasi `min_silence_duration_ms`, ambang peluang tanpa ucapan, log-probabilitas rata-rata, dan aturan pengulangan n-gram pada 20 klip hening dan seluruh set uji. Pemeriksaan manual 100 segmen untuk penanda waktu ±1 detik.
- **Kriteria penerimaan:** ≥ 95% dari 20 klip hening menghasilkan keluaran kosong (≤ 2 kata). 0 transkrip dengan n-gram berulang > 5 kali berturut-turut. ≥ 95% segmen sampel dalam ±1 detik. Parameter final dicatat untuk TK-032.

---

## Fase 1: MVP, Jalur API (VPS)

### TK-020: Skema basis data dan migrasi
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-001
- **Rujukan:** PRD 4.4, 4.5
- **Pekerjaan:** SQLite mode WAL, migrasi berversi (Alembic atau skrip sederhana), lapisan akses data untuk semua tabel di 4.4. Indeks untuk `jobs(state, dibuat_pada)` dan `jobs(user_id)`. Pragma yang aman (`foreign_keys`, `busy_timeout`).
- **Kriteria penerimaan:** Migrasi naik dan turun berjalan di mesin bersih. Uji konkurensi menunjukkan pengambilan job atomik tidak menghasilkan dua pekerja untuk satu job.

### TK-021: Autentikasi Google, allowlist, sesi, Turnstile
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-020, TK-003
- **Rujukan:** PRD 4.9, D-04
- **Pekerjaan:** Google OIDC, pemeriksaan allowlist, sesi cookie (`HttpOnly`, `Secure`, `SameSite=Lax`, domain bersama), CLI untuk menambah dan menghapus email di allowlist, verifikasi Turnstile sebagai dependensi, pembatasan laju dasar.
- **Kriteria penerimaan:** Email di luar allowlist ditolak dengan pesan jelas. Sesi dicabut saat keluar. Semua endpoint pengguna menolak permintaan tanpa sesi. Kueri difilter `user_id` (uji akses silang pengguna gagal sebagaimana mestinya).

### TK-022: Persetujuan dan pemberitahuan privasi
- **Jalur / ukuran / tipe:** API / S / kode
- **Dependensi:** TK-021, TK-060 (teks versi pertama)
- **Rujukan:** PRD US-06
- **Pekerjaan:** Endpoint `POST/DELETE /api/consents`, penyimpanan versi dokumen dan waktu, pemblokiran unggahan sebelum persetujuan, penarikan persetujuan memicu penghentian pemrosesan dan penghapusan ≤ 3 × 24 jam (menjadwalkan penghapusan).
- **Kriteria penerimaan:** Unggahan pertama tanpa persetujuan ditolak. Persetujuan tercatat dengan waktu dan versi. Penarikan menjadwalkan penghapusan dan membatalkan job aktif.

### TK-023: Alur unggah multipart ke R2
- **Jalur / ukuran / tipe:** API / L / kode
- **Dependensi:** TK-020, TK-021, TK-022, TK-003 (atau MinIO dari TK-002)
- **Rujukan:** PRD 4.6, US-01, D-13
- **Pekerjaan:** Endpoint inisiasi, URL potongan bertanda tangan, daftar potongan untuk pelanjutan, penyelesaian dengan pemeriksaan ringan (ukuran, tipe konten, tanda tangan berkas), pembatalan unggahan menggantung. Plafon global 8 GB. Kunci objek tanpa nama berkas asli.
- **Kriteria penerimaan:** Berkas 200 MB terunggah dalam potongan 8 MiB. Pemutusan koneksi di tengah dan pelanjutan berhasil tanpa mengulang dari awal. Berkas > 200 MB atau tipe terlarang ditolak sebelum unggahan dimulai. Pemeriksaan ringan selesai ≤ 5 detik.

### TK-024: Siklus job, kuota, dan pembatasan
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-023
- **Rujukan:** PRD 4.5, US-02, US-07, 2.4
- **Pekerjaan:** Mesin status, posisi antrean dan perkiraan waktu, `usage_ledger`, kuota harian per hari lokal UTC+7, batas job aktif, pesan dan waktu reset, kedaluwarsa 72 jam.
- **Kriteria penerimaan:** Kuota habis menghasilkan pesan dengan waktu reset. Job yang menunggu > 72 jam menjadi `expired`, audio terjadwal dihapus, dan pengguna diberi tahu. Transisi ilegal ditolak oleh uji unit.

### TK-025: API pekerja (klaim, detak, hasil, gagal)
- **Jalur / ukuran / tipe:** API / L / kode
- **Dependensi:** TK-024
- **Rujukan:** PRD 4.7, AI-09, D-03
- **Pekerjaan:** Autentikasi token pekerja (hash, rotasi), klaim long-poll ≤ 25 detik dengan sewa 5 menit, URL GET bertanda tangan ke R2 untuk pekerja, detak yang membawa sinyal `cancel`, penerimaan hasil (validasi skema), penanganan gagal dan batas 3 percobaan, penyapu sewa kedaluwarsa, deteksi pekerja tidak aktif (90 detik) untuk status situs.
- **Kriteria penerimaan:** Uji dengan pekerja palsu: job selesai ujung ke ujung. Pekerja yang berhenti membuat job kembali ke antrean dan percobaan bertambah. Setelah 3 percobaan job `failed`. Token salah ditolak.

### TK-026: API transkrip (segmen, penyuntingan, pembicara)
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-025
- **Rujukan:** PRD US-03, US-08
- **Pekerjaan:** Baca transkrip, `PATCH` segmen dengan `versi` untuk deteksi tabrakan, ganti nama pembicara, pindahkan segmen ke pembicara lain, URL audio bertanda tangan sementara hanya selama audio ada.
- **Kriteria penerimaan:** Penyuntingan tidak mengubah penanda waktu. Suntingan bertahan setelah muat ulang. URL audio tidak diberikan setelah audio terhapus.

### TK-027: Ekspor TXT, SRT, VTT, DOCX
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-026
- **Rujukan:** PRD US-04, US-08
- **Pekerjaan:** Pembuat ekspor yang mencerminkan suntingan terbaru dan nama pembicara. SRT dan VTT divalidasi dengan pemeriksa format. DOCX dengan `python-docx`.
- **Kriteria penerimaan:** SRT dan VTT lolos pemeriksa dan dapat dimuat di pemutar populer. Awalan "Nama:" benar. Ekspor bekerja walaupun audio sudah dihapus.

### TK-028: Retensi dan penghapusan (K4)
- **Jalur / ukuran / tipe:** API / M / kode
- **Dependensi:** TK-024, TK-026
- **Rujukan:** PRD 4.12, US-05, K4, AI-10
- **Pekerjaan:** Penjadwal 15 menit untuk menghapus audio R2 ≤ 24 jam setelah selesai, gagal, kedaluwarsa, atau dibatalkan. Penjadwal harian untuk transkrip 30 hari. `DELETE /api/jobs/{id}` dan `DELETE /api/me`. Audit K4 harian (bucket R2, direktori VPS, dan laporan direktori kerja dari pekerja). Cadangan ≤ 7 hari.
- **Kriteria penerimaan:** Uji otomatis dengan jam yang dimajukan membuktikan audio terhapus ≤ 24 jam. Hapus akun menghilangkan job, segmen, audio, dan sesi. Audit K4 memberi peringatan bila ada objek di luar retensi.

### TK-029: Observabilitas dan metrik
- **Jalur / ukuran / tipe:** API / S / kode
- **Dependensi:** TK-025
- **Rujukan:** PRD 3.4.7, 4.15
- **Pekerjaan:** Log JSON tanpa nama berkas dan teks, `GET /healthz`, metrik per job (xRT, status, proporsi keyakinan rendah, rasio penyuntingan), halaman atau skrip admin ringkas (job per status, median xRT, tingkat gagal, status pekerja, R2 terpakai).
- **Kriteria penerimaan:** Pengujian log memastikan tidak ada nama berkas atau teks transkrip di keluaran log. Metrik rasio penyuntingan dihitung tanpa menyimpan teks sunting.

---

## Fase 1: MVP, Jalur Pekerja (Laptop)

### TK-030: Kerangka pekerja
- **Jalur / ukuran / tipe:** WRK / M / kode
- **Dependensi:** TK-001, TK-005
- **Rujukan:** PRD 4.7, 4.8, D-03
- **Pekerjaan:** Konfigurasi (URL API, token), klien HTTP dengan jeda bertingkat dan batas waktu, lingkaran klaim → proses → kirim, detak 30 detik, penghentian rapi (Ctrl+C membebaskan job), penanganan sinyal `cancel`, pendaftaran dan `ping` versi.
- **Kriteria penerimaan:** Pekerja berjalan terhadap server tiruan dan terhadap API nyata (setelah TK-025). Dihentikan di tengah job, job kembali ke antrean tanpa berkas tersisa.

### TK-031: Validasi dan normalisasi media
- **Jalur / ukuran / tipe:** WRK / M / kode
- **Dependensi:** TK-030
- **Rujukan:** PRD AI-01, AI-02, R-05
- **Pekerjaan:** `ffprobe` (kontainer, durasi, aliran audio), batas durasi 90 menit, `ffmpeg` ke WAV 16 kHz mono dengan batas waktu 10 menit, `-protocol_whitelist file,pipe`, tanpa jaringan, proses anak dengan batas memori, penanganan galat yang menghasilkan pesan manusiawi.
- **Kriteria penerimaan:** Berkas tanpa aliran audio, rusak, atau > 90 menit ditolak ≤ 60 detik dengan kode galat yang benar. Uji dengan sampel media cacat (disusun sendiri) tidak membuat proses menggantung.

### TK-032: Tahap transkripsi
- **Jalur / ukuran / tipe:** WRK / L / kode
- **Dependensi:** TK-031, TK-013 (parameter final) atau parameter awal sementara
- **Rujukan:** PRD 3.1, AI-03 sampai AI-06
- **Pekerjaan:** `faster-whisper` dengan versi dipatok, VAD, parameter dekode, bahasa `id` default, anti-halusinasi dan anti-pengulangan, keluaran segmen dengan skor keyakinan, pencatatan versi model, pembebasan VRAM setelah tahap.
- **Kriteria penerimaan:** Hasil pada set uji sesuai laporan TK-013. VRAM puncak ≤ 5 GB. Dua kali proses pada masukan sama berselisih ≤ 0,5 poin WER.

### TK-033: Pengemasan hasil dan higiene data
- **Jalur / ukuran / tipe:** WRK / S / kode
- **Dependensi:** TK-032
- **Rujukan:** PRD AI-10, 4.8
- **Pekerjaan:** Pengiriman hasil ke VPS, penghapusan berkas kerja di blok `finally`, log tanpa teks dan nama berkas, laporan direktori kerja bersih untuk audit K4.
- **Kriteria penerimaan:** Setelah job sukses, gagal, atau dibatalkan, direktori kerja kosong (diuji otomatis). Pencarian string transkrip di log tidak menemukan apa pun.

### TK-034: Perlindungan laptop
- **Jalur / ukuran / tipe:** WRK / S / kode
- **Dependensi:** TK-030
- **Rujukan:** PRD AI-08
- **Pekerjaan:** Cek baterai (< 30% dan tidak dicas → tidak mengambil job), cek suhu GPU dengan `nvidia-smi` (ambang dikalibrasi di benchmark), pencegah tidur Windows selama job (`SetThreadExecutionState`) dan dilepas saat idle.
- **Kriteria penerimaan:** Dengan kabel dicabut dan baterai < 30% pekerja tidak mengambil job baru. Laptop tidak tidur selama job berjalan (diuji dengan job panjang).

### TK-035: Penanganan OOM dan percobaan ulang
- **Jalur / ukuran / tipe:** WRK / S / kode
- **Dependensi:** TK-032
- **Rujukan:** PRD AI-07, AI-09
- **Pekerjaan:** Tangkap OOM CUDA, ulangi sekali dengan batch setengah, lalu laporkan `failed (kapasitas)`. Pastikan VRAM bersih setelah galat.
- **Kriteria penerimaan:** Uji dengan batas VRAM buatan memicu jalur ulang lalu gagal dengan pesan yang dapat dipahami. Job berikutnya berjalan normal.

---

## Fase 1: MVP, Jalur Web

### TK-040: Scaffold web dan klien API
- **Jalur / ukuran / tipe:** WEB / M / kode
- **Dependensi:** TK-001
- **Rujukan:** PRD 4.2, 4.3
- **Pekerjaan:** Vite + React + TS, perutean, klien API terhasilkan dari OpenAPI, penanganan galat standar (pesan Indonesia), tema dan komponen dasar, pengaturan Pages, variabel lingkungan untuk URL API, server tiruan untuk pengembangan.
- **Kriteria penerimaan:** `make dev-web` tampil dengan server tiruan. Penerapan pratinjau di Pages berhasil.

### TK-041: Login dan persetujuan
- **Jalur / ukuran / tipe:** WEB / M / kode
- **Dependensi:** TK-040, TK-022
- **Rujukan:** PRD US-06, 2.2
- **Pekerjaan:** Tombol masuk Google, halaman pemberitahuan privasi, persetujuan eksplisit, deklarasi ≥ 18 tahun, tombol tarik persetujuan, halaman atribusi model.
- **Kriteria penerimaan:** Pengguna tanpa persetujuan tidak dapat membuka halaman unggah. Teks privasi berbahasa Indonesia sederhana dan sesuai versi yang dicatat.

### TK-042: Unggah dapat dilanjutkan dan kuota
- **Jalur / ukuran / tipe:** WEB / L / kode
- **Dependensi:** TK-041, TK-023, TK-024
- **Rujukan:** PRD US-01, US-07, 4.6
- **Pekerjaan:** Pemilih berkas, pemeriksaan ekstensi dan ukuran sebelum unggah, pembacaan durasi sebagai petunjuk, potongan 8 MiB dengan 3 unggahan paralel, bilah kemajuan, pelanjutan setelah koneksi putus (`ListParts`), tampilan sisa kuota dan waktu reset, pilihan bahasa, Turnstile.
- **Kriteria penerimaan:** Unggahan 200 MB berhasil di jaringan normal. Mematikan jaringan di tengah lalu menyalakan lagi melanjutkan dari potongan terakhir. Pelanggaran batas menampilkan pesan yang menyebut batas yang dilanggar.

### TK-043: Daftar job dan halaman status
- **Jalur / ukuran / tipe:** WEB / M / kode
- **Dependensi:** TK-042
- **Rujukan:** PRD US-02
- **Pekerjaan:** Polling tiap 5 detik, status menunggu/diproses/selesai/gagal, posisi antrean dan perkiraan waktu, pemberitahuan "pemrosesan tertunda" saat pekerja tidak aktif, pesan galat manusiawi.
- **Kriteria penerimaan:** Status berubah tanpa muat ulang dengan jeda ≤ 10 detik. Saat pekerja mati tidak ada status "diproses" palsu.

### TK-044: Editor transkrip dengan audio tersinkron
- **Jalur / ukuran / tipe:** WEB / L / kode
- **Dependensi:** TK-043, TK-026
- **Rujukan:** PRD US-03, AI-06
- **Pekerjaan:** Tampilan per segmen dengan penanda waktu, klik segmen memutar audio dari titik itu (selisih ≤ 1 detik), penyorotan segmen berkeyakinan rendah, simpan otomatis ≤ 5 detik dengan penanganan tabrakan versi, pemutar disembunyikan dengan keterangan setelah audio dihapus.
- **Kriteria penerimaan:** Suntingan bertahan setelah muat ulang. Pemutar bekerja pada MP3, M4A, WebM, dan Opus. Setelah audio dihapus, penyuntingan tetap berfungsi.

### TK-045: Ekspor dan hapus data
- **Jalur / ukuran / tipe:** WEB / S / kode
- **Dependensi:** TK-044, TK-027, TK-028
- **Rujukan:** PRD US-04, US-05
- **Pekerjaan:** Tombol ekspor (TXT, SRT, VTT, DOCX), hapus per job dan hapus akun dengan konfirmasi, tampilan konfirmasi dan ringkasan kebijakan retensi.
- **Kriteria penerimaan:** Ekspor mencerminkan suntingan terbaru. Setelah konfirmasi, job hilang dari daftar dan pengguna melihat pesan penghapusan.

---

## Fase 1: Dokumen, Keamanan, dan QA

### TK-060: Pemberitahuan privasi, ROPA, dan DPIA-lite
- **Jalur / ukuran / tipe:** DOC / M / manual
- **Dependensi:** T-14 (nama produk), T-12 (verifikasi hukum)
- **Rujukan:** PRD 4.11, US-06, D-05, D-17
- **Pekerjaan:** Pemberitahuan privasi (data dikumpulkan, tujuan, lokasi pemrosesan termasuk R2 dan VPS, lama simpan, ciri suara sementara pada pelabelan pembicara, metrik tanpa teks, cadangan ≤ 7 hari, cara menarik persetujuan). ROPA ringkas. DPIA-lite (risiko, mitigasi). Prosedur kebocoran ≤ 3 × 24 jam di runbook. Beri tahu dosen pembimbing dan catat hasilnya (T-06).
- **Kriteria penerimaan:** Teks dapat dipahami orang awam. Setiap klaim di dokumen cocok dengan perilaku sistem di PRD (diperiksa dalam tinjauan). Daftar item hukum yang diverifikasi ke teks resmi tercatat.

### TK-061: Tinjauan model ancaman dan daftar periksa keamanan
- **Jalur / ukuran / tipe:** QA / M / manual + kode
- **Dependensi:** TK-025, TK-023, TK-031
- **Rujukan:** PRD 4.10, R-05
- **Pekerjaan:** Telusuri tabel STRIDE terhadap kode nyata. Uji akses silang pengguna, URL bertanda tangan kedaluwarsa, token pekerja salah, unggahan di luar kuota, media berbahaya. Periksa rahasia di repo dan log. Pastikan akun pekerja tanpa hak admin.
- **Kriteria penerimaan:** Setiap baris STRIDE punya bukti uji atau catatan keputusan. Tidak ada temuan tinggi yang terbuka.

### TK-062: Uji ujung ke ujung, uji beban, dan latihan kegagalan
- **Jalur / ukuran / tipe:** QA / L / kode + manual
- **Dependensi:** TK-045, TK-035, TK-028
- **Rujukan:** PRD 4.13, 4.14, K2, K3, K4
- **Pekerjaan:**
  - E2E: unggah → transkrip → sunting → ekspor → hapus (Playwright atau sejenis), memakai pekerja asli di laptop.
  - `k6` terhadap API pada VPS: ukur RAM, latensi, dan tingkat galat.
  - Latihan kegagalan dari tabel 4.14: matikan pekerja, cabut baterai, putus jaringan, penuhkan disk uji, rusakkan berkas basis data pada salinan.
  - Hitung K2, K3, K4 dari log nyata.
- **Kriteria penerimaan:** Semua mode kegagalan menunjukkan perilaku dan waktu pemulihan sesuai 4.14 atau dicatat sebagai penyimpangan. Laporan K2, K3, K4 di `docs/`.

### TK-063: Kesiapan pilot tertutup
- **Jalur / ukuran / tipe:** QA / S / manual
- **Dependensi:** TK-060, TK-061, TK-062
- **Rujukan:** PRD 5.1 (kriteria keluar Fase 1), D-04
- **Pekerjaan:** Daftar undangan, panduan singkat pengguna, jam layanan yang diumumkan, saluran umpan balik, rencana mematikan pilot (kill switch: nonaktifkan unggahan lewat satu pengaturan).
- **Kriteria penerimaan:** Semua kriteria keluar Fase 1 terpenuhi dan terdokumentasi. Kill switch diuji.

---

## Fase 2: Pelabelan Pembicara

### TK-050: Spike diarisasi di Windows (GERBANG)
- **Jalur / ukuran / tipe:** SPK / M / riset
- **Dependensi:** TK-005
- **Rujukan:** PRD 3.1, AI-11, R-02, T-10, T-11
- **Pekerjaan:**
  - Pasang `pyannote.audio` dan PyTorch CUDA berdampingan dengan `faster-whisper`. Setujui syarat model dan buat token Hugging Face.
  - Jalankan `speaker-diarization-community-1` pada beberapa rekaman 2 sampai 4 pembicara (rekaman sendiri). Ukur VRAM puncak, waktu, dan jumlah pembicara terdeteksi.
  - Bandingkan sepintas dengan kandidat cadangan `diarize` (CPU).
  - Putuskan: Windows asli atau WSL2, dan versi pustaka yang dipatok.
- **Kriteria penerimaan:** Catatan keputusan (ADR) dengan angka VRAM dan waktu. Jawaban T-11. Bila tidak layak, rekomendasi jalur cadangan.

### TK-051: Tahap diarisasi di pekerja
- **Jalur / ukuran / tipe:** SPK / M / kode
- **Dependensi:** TK-050, TK-032
- **Rujukan:** PRD AI-11, AI-13, AI-14
- **Pekerjaan:** Setelah transkripsi: bebaskan VRAM Whisper, muat model diarisasi, jalankan dengan `min_speakers` dan `max_speakers` (maksimum 8), pakai `exclusive_speaker_diarization`, bebaskan model. Kegagalan menghasilkan job tanpa label dengan penanda. Tidak ada embedding yang disimpan.
- **Kriteria penerimaan:** VRAM puncak ≤ 5 GB di setiap tahap. Kegagalan diarisasi tidak menggagalkan job. Tidak ada berkas embedding tersisa setelah job.

### TK-052: Penggabungan transkrip dan pembicara
- **Jalur / ukuran / tipe:** SPK / M / kode
- **Dependensi:** TK-051
- **Rujukan:** PRD AI-12
- **Pekerjaan:** Algoritme irisan terbesar per segmen, aturan untuk segmen tanpa irisan, uji unit dengan kasus tumpang tindih dan giliran pendek. Versi kata-kata (`word_timestamps`) untuk memecah segmen di tengah giliran.
- **Kriteria penerimaan:** Uji unit mencakup tumpang tindih, hening panjang, dan satu pembicara saja. Pemecahan di tengah segmen tidak mengubah teks gabungan.

### TK-053: Set uji multi-pembicara dan evaluasi DER
- **Jalur / ukuran / tipe:** SPK / L / manual + kode
- **Dependensi:** TK-050
- **Rujukan:** PRD 3.4.9, K6, T-10
- **Pekerjaan:** Rekam 20 klip × 3 sampai 5 menit dengan 2 sampai 5 pembicara (persetujuan semua pembicara). Anotasi giliran bicara oleh 2 penyunting. Skrip DER dengan `pyannote.metrics` (collar 0,25 s), laporan per jumlah pembicara dan tingkat tumpang tindih, serta akurasi jumlah pembicara.
- **Kriteria penerimaan:** Laporan DER tersedia. Keputusan per 3.4.9 (lulus, atau label eksperimental) tercatat di Lampiran A.

### TK-054: Kuota 2× dan pengembalian saat gagal
- **Jalur / ukuran / tipe:** SPK / S / kode
- **Dependensi:** TK-024, TK-051
- **Rujukan:** PRD US-07, US-08
- **Pekerjaan:** Biaya kuota 2× untuk job berdiarisasi, entri `kembalikan` di `usage_ledger` bila diarisasi gagal, tampilan biaya sebelum unggah.
- **Kriteria penerimaan:** Job berdiarisasi mengurangi kuota 2×. Saat diarisasi gagal, kuota tambahan kembali dan pengguna melihat pemberitahuan.

### TK-046: Antarmuka pembicara
- **Jalur / ukuran / tipe:** WEB / M / kode
- **Dependensi:** TK-044, TK-026, TK-052
- **Rujukan:** PRD US-08
- **Pekerjaan:** Sakelar "Pisahkan pembicara" saat unggah dengan keterangan 2× kuota dan lebih lama, petunjuk jumlah pembicara, label per segmen, ganti nama label, pindahkan satu segmen, ekspor dengan nama pembicara, pemberitahuan privasi tentang ciri suara sementara.
- **Kriteria penerimaan:** Penggantian nama berlaku untuk semua segmen berlabel dan tersimpan. Ekspor memakai nama. Bila label tidak tersedia, transkrip tampil tanpa label dengan pemberitahuan.

---

## Fase 3: Opsional

### TK-070: Perluasan (hanya setelah telaah hukum dan DPIA lengkap)
- **Jalur / ukuran / tipe:** DOC / L / manual
- **Dependensi:** TK-063, TK-053, T-12
- **Rujukan:** PRD 5.1 Fase 3, 2.5
- **Deskripsi:** Pendaftaran yang lebih terbuka, tempat inferensi pengganti bila laptop tidak memadai, dan pengenalan pembicara lintas rekaman (data biometrik, memerlukan DPIA dan persetujuan terpisah). Tidak dikerjakan sebelum kriteria keluar Fase 2 terpenuhi.
- **Kriteria penerimaan:** Dokumen keputusan (ADR) dengan hasil telaah hukum dan DPIA. Tiket implementasi baru dibuat setelahnya.

---

## Template Tiket Baru

```
### TK-XXX: Judul singkat
- Jalur / ukuran / tipe:
- Dependensi:
- Rujukan: (bagian PRD, US, AI, K, D, T)
- Deskripsi / Pekerjaan:
- Kriteria penerimaan: (dapat diuji, ada angka bila ada)
- Catatan keputusan: (bila GERBANG, tulis di PRD Lampiran A)
```
