# ADR 001: Transkripsi lewat Cloudflare Workers AI

Status: berlaku untuk versi web saat ini, perlu disetujui tim.

## Konteks

PRD merancang laptop RTX 4050 + VPS + R2, tetapi bagian itu belum dibangun.
Tim butuh web yang sudah bisa dipakai untuk mentranskrip audio.

## Keputusan

Transkripsi berjalan di `@cf/openai/whisper-large-v3-turbo` lewat Pages Function
(`apps/web/functions/api/transcribe.ts`, binding `AI` di `apps/web/wrangler.toml`).
Browser mendekode audio, memotongnya sekitar 60 detik di titik tersepi, lalu
mengirim potongan sebagai WAV 16 kHz. Audio dan transkrip tidak disimpan di server.

## Penyimpangan dari PRD

- D-03 dan D-11: audio diproses Cloudflare Workers AI, bukan laptop pengelola.
- Tanpa login, allowlist, Turnstile, dan kuota per pengguna: situs terbuka untuk umum.
- Tanpa pelabelan pembicara dan tanpa riwayat job.
- Target WER (K1) belum diukur pada mesin ini.

## Konsekuensi

- Kuota gratis 10.000 neuron per hari (sekitar 214 menit audio) dipakai bersama
  semua pengunjung dan terisi lagi pukul 00.00 UTC.
- Karena terbuka, siapa pun bisa menghabiskan kuota harian. Bila terjadi, tambahkan
  Turnstile atau aturan rate limit Cloudflare.
- Pemberitahuan privasi (TK-060) tetap perlu ditulis sebelum dipakai untuk data orang lain.
