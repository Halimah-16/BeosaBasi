# PRD: Layanan Transkripsi Suara-ke-Teks Bahasa Indonesia (Whisper large-v3-turbo, Self-Hosted)

| | |
|---|---|
| **Nama produk** | [TBD] |
| **Versi dokumen** | 1.0 (draf lengkap) |
| **Tanggal** | 2 November 2026 |
| **Status** | Semua bagian (1 sampai 5) sudah ditulis. v1.0 menambahkan: pelabelan pembicara (US-08, K6, AI-11 sampai AI-14), keputusan T-07 (Windows asli), T-08 (VPS 2 vCPU / 2 GB), T-09 (tanpa tenggat), Bagian 4 (spesifikasi teknis), dan Bagian 5 (risiko dan peta jalan). Pecahan pekerjaan ada di `TICKETS.md`. Nilai yang masih [T] harus diukur pada Fase 0. |
| **Bahasa dokumen** | Bahasa Indonesia |

**Legenda status klaim**

- **[V]** Terverifikasi dari sumber yang dicantumkan di Lampiran C (tanggal akses 2 November 2026).
- **[A]** Asumsi atau keputusan awal yang dipilih penulis. Boleh diubah.
- **[T]** TBD. Belum diketahui dan tidak boleh ditebak. Harus diukur atau diputuskan.

---

## 1. Ringkasan Eksekutif

### 1.1 Pernyataan Masalah

Orang Indonesia yang perlu menyalin rekaman wawancara, kuliah, rapat, atau pesan suara panjang ke teks harus memilih antara mengetik manual, memakai layanan berbayar yang audionya diproses di luar negeri, atau memakai alat yang akurasinya buruk pada bahasa Indonesia sehari-hari. [A]

### 1.2 Solusi yang Diusulkan

Layanan web gratis untuk individu: pengguna mengunggah berkas audio atau video, lalu menerima transkrip bahasa Indonesia berpenanda waktu yang bisa disunting dan diekspor. Inferensi memakai model Whisper large-v3-turbo yang berjalan di laptop pengelola (GPU RTX 4050 6 GB) yang hanya berperan sebagai pekerja inferensi. Antarmuka web statis berada di Cloudflare Pages. API, basis data, dan antrean job berjalan di VPS milik pengelola. Audio disimpan sementara di Cloudflare R2. Paket gratis Cloudflare juga dipakai untuk DNS, proksi/WAF, dan Turnstile. Pengguna dapat memilih pelabelan pembicara ("Pembicara 1, 2, ...") di dalam satu rekaman. [A]

### 1.3 Kriteria Keberhasilan

| ID | Indikator | Target | Cara ukur | Status |
|---|---|---|---|---|
| K1 | Akurasi transkripsi bahasa Indonesia | WER ≤ 15% pada set uji internal | Set uji MVP: 60 klip × 1 menit (1 jam) dari 5 kategori × 12 klip (wawancara, rapat, pesan suara WhatsApp, audio berderau, campur Indonesia-Inggris), diperluas ke ≥ 3 jam pada v1.1. Transkrip acuan dibuat 2 penyunting independen dan semua pembicara memberi persetujuan. Skor `jiwer` setelah normalisasi (lihat 3.4). | [A] ambang awal, dikalibrasi setelah benchmark |
| K2 | Kecepatan penyelesaian | p95 waktu total (antre + proses) ≤ 25% durasi audio untuk file ≤ 30 menit, saat antrean ≤ 5 job, tanpa pelabelan pembicara. Dengan pelabelan: ≤ 60%. | Uji beban `k6` dan log produksi, dihitung hanya selama pekerja aktif | [A] angka dikalibrasi setelah kecepatan RTX 4050 terukur (3.4.4) [T] |
| K3 | Keandalan job | ≥ 98% job berkas valid selesai tanpa intervensi manual selama 30 hari berturut-turut, dihitung untuk job yang diunggah saat pekerja aktif. Job yang diunggah saat pekerja mati selesai ≤ 60 menit setelah pekerja aktif kembali, atau kedaluwarsa setelah 72 jam. | Metrik status job di basis data VPS | [A] |
| K4 | Kepatuhan retensi | 100% berkas audio terhapus ≤ 24 jam setelah job selesai, gagal, atau kedaluwarsa | Tes otomatis harian yang memindai bucket R2, penyimpanan VPS, dan direktori kerja laptop | [A] |
| K5 | Biaya tambahan | Rp0 di luar VPS yang sudah ada, pada beban pilot tertutup (≤ 50 pengguna undangan) | Tagihan akun Cloudflare dan VPS | [A] |
| K6 | Kualitas pelabelan pembicara | DER ≤ 25% (collar 0,25 s) pada 20 klip multi-pembicara | `pyannote.metrics` terhadap anotasi giliran bicara oleh 2 penyunting | [A] ambang awal. Angka literatur sekitar 17 sampai 20% pada benchmark non-Indonesia [V] |

### 1.4 Batasan Kunci yang Mempengaruhi Seluruh Dokumen

- Transkripsi berjalan di laptop RTX 4050 6 GB yang menyala hanya sewaktu pemilik memakainya. Ketersediaan transkripsi tidak bisa lebih tinggi daripada ketersediaan laptop itu. Situs dan antrean tetap hidup di VPS. [A]
- Batas badan permintaan yang melewati proksi Cloudflare adalah 100 MB pada paket Free. [V] Karena VPS berada di belakang proksi, unggahan audio besar dikirim dalam potongan kecil (lihat US-01).
- Workers paket Free dibatasi 100.000 permintaan per hari dan 10 ms waktu CPU per pemanggilan. [V] Berlaku hanya bila Workers dipakai. Arsitektur final diputuskan di Bagian 4.
- Video dan file besar yang di-host di luar Cloudflare tetap dibatasi pada CDN Cloudflare. [V] Karena itu audio tidak disajikan dari VPS lewat proksi, melainkan disimpan dan disajikan dari R2. Teks klausul lengkap di Service-Specific Terms belum dibaca. [T]
- VPS hanya 2 vCPU dan 2 GB RAM. Karena itu VPS tidak menjalankan inferensi, dekode media berat, maupun basis data server terpisah. Tugas VPS dibatasi pada API, basis data SQLite, antrean, dan penjadwal penghapusan. [A]
- Laptop memakai Windows asli (Python + CUDA). Pemasangan CUDA, `faster-whisper`, dan `pyannote.audio` pada Windows harus lolos uji di Fase 0. Cadangannya WSL2. [A]
- Tidak ada aturan kampus tertulis dan tidak ada tenggat. Jadwal di Bagian 5 memakai kriteria keluar, bukan tanggal. [A]
- Konteks proyek: proyek kuliah dengan target kualitas produksi. Pilot dibatasi tertutup (undangan) sampai tinjauan hukum dan kebijakan kampus selesai. [A]
- UU PDP No. 27/2022 berlaku penuh. PP 33/2026 diundangkan 16 Juli 2026 dan mulai berlaku 16 Januari 2027. [V] (sumber sekunder, perlu verifikasi ke teks resmi)

---

## 2. Pengalaman Pengguna dan Fungsionalitas

### 2.1 Persona Pengguna

| Persona | Kebutuhan | Kekhawatiran utama |
|---|---|---|
| **Dina, mahasiswa S2** merekam wawancara penelitian 45 sampai 90 menit | Transkrip berpenanda waktu untuk dikutip | Data narasumber tidak boleh bocor |
| **Raka, jurnalis dan kreator konten** membuat subtitle dari video | Ekspor SRT dan VTT yang rapi | Kecepatan dan akurasi nama orang atau istilah |
| **Bu Sari, pekerja kantoran** menerima pesan suara WhatsApp panjang (berkas .opus) | Membaca isi tanpa memutar audio | Kemudahan: tanpa instal aplikasi, tanpa bayar |

### 2.2 Alur Utama Pengguna

1. Pengguna membuka situs dan masuk (metode masuk lihat D-04, Lampiran A).
2. Pengguna membaca dan menyetujui pemberitahuan privasi (eksplisit, bisa ditarik kembali).
3. Pengguna memilih berkas dan bahasa (default: Indonesia).
4. Berkas diunggah bertahap. Unggahan bisa dilanjutkan bila koneksi putus.
5. Pengguna melihat status: menunggu, diproses, selesai, atau gagal, beserta posisi antrean.
6. Pengguna membuka transkrip, memutar audio sinkron, menyunting teks.
7. Pengguna mengekspor atau menghapus data.

### 2.3 User Stories dan Kriteria Penerimaan

**US-01: Unggah dan transkripsi berkas**
*Sebagai pengguna, saya ingin mengunggah berkas audio atau video agar saya mendapat teksnya tanpa mengetik.*

- Format yang diterima: MP3, M4A, WAV, FLAC, OGG/Opus (termasuk pesan suara WhatsApp), MP4, WebM. [A]
- Batas per berkas: ≤ 200 MB dan ≤ 90 menit. Berkas di atas batas ditolak dengan pesan yang menyebut batas yang dilanggar, sebelum unggahan dimulai. [A]
- Unggahan dikirim langsung ke R2 dalam potongan 8 MiB lewat URL bertanda tangan, tidak melewati VPS. [V] Bila koneksi putus, unggahan dilanjutkan dari potongan terakhir yang berhasil, tanpa mengulang dari awal.
- Pemeriksaan ringan di VPS (ukuran, tipe konten, tanda tangan berkas pada potongan pertama) berlangsung ≤ 5 detik setelah unggahan selesai. Pemeriksaan penuh (`ffprobe`, durasi) dilakukan pekerja saat mengambil job, dan berkas rusak ditandai gagal ≤ 60 detik setelah itu, dengan alasan yang bisa dipahami. [A]
- Bahasa default adalah Indonesia. Pengguna bisa memilih Inggris atau deteksi otomatis. [A] Perilaku pada audio campur Indonesia-Inggris harus diuji pada benchmark [T].

**US-02: Memantau status job**
*Sebagai pengguna, saya ingin tahu pekerjaan saya sedang apa agar saya tidak menunggu tanpa kepastian.*

- Status yang tampil: menunggu, diproses, selesai, gagal.
- Selama menunggu, tampil posisi antrean dan perkiraan waktu. Perkiraan dihitung dari durasi audio dan kecepatan proses terukur.
- Bila perangkat lokal tidak aktif, situs menampilkan pemberitahuan bahwa pemrosesan tertunda, tidak menampilkan status "diproses" palsu. Job tidak hilang dan berjalan otomatis ketika perangkat kembali aktif. Pekerja dianggap tidak aktif bila tidak mengirim detak (heartbeat) dalam 90 detik. Job yang menunggu lebih dari 72 jam dibatalkan, audio dihapus, dan pengguna diberi tahu. [A]
- Halaman status memperbarui sendiri dengan jeda ≤ 10 detik tanpa muat ulang manual. [A]

**US-03: Meninjau dan menyunting transkrip**
*Sebagai pengguna, saya ingin menyunting hasil agar kesalahan nama dan istilah bisa diperbaiki.*

- Transkrip tampil per segmen dengan penanda waktu.
- Mengklik segmen memutar audio dari titik waktu itu dengan selisih ≤ 1 detik, selama audio masih tersimpan (≤ 24 jam setelah job selesai). Setelah audio dihapus, pemutar disembunyikan dengan keterangan alasannya, dan penyuntingan teks tetap berfungsi. [A]
- Penyuntingan tersimpan otomatis dalam ≤ 5 detik dan bertahan setelah muat ulang halaman.
- Penyuntingan tidak mengubah penanda waktu segmen.

**US-04: Ekspor**
*Sebagai pengguna, saya ingin mengunduh transkrip dalam format yang saya butuhkan.*

- Format ekspor: TXT, SRT, VTT, DOCX. [A]
- SRT dan VTT valid menurut pemeriksa format standar dan dapat dimuat di pemutar video populer.
- Ekspor mencerminkan hasil sunting terbaru.

**US-05: Menghapus data saya**
*Sebagai pengguna, saya ingin menghapus rekaman dan transkrip saya kapan saja agar data saya tidak tersimpan tanpa kendali saya.*

- Tombol hapus tersedia per job dan untuk seluruh akun.
- Setelah dikonfirmasi, data terhapus dari penyimpanan dan basis data dalam ≤ 24 jam, dan pengguna melihat konfirmasi. [A]
- Permintaan hak subjek data (akses, salinan, penarikan persetujuan) dapat dipenuhi dalam 3 × 24 jam. [V] (menurut ringkasan PP 33/2026, perlu verifikasi hukum)
- Audio otomatis terhapus ≤ 24 jam setelah job selesai, gagal, atau kedaluwarsa. Transkrip otomatis terhapus pada hari ke-30 kecuali pengguna menghapus lebih dulu. [A]

**US-06: Persetujuan dan transparansi privasi**
*Sebagai pengguna, saya ingin tahu apa yang terjadi pada suara saya sebelum saya mengunggahnya.*

- Pemberitahuan privasi berbahasa Indonesia sederhana menyebutkan: data apa yang dikumpulkan, tujuan, lokasi pemrosesan, lama simpan, dan cara menarik persetujuan.
- Unggahan pertama diblokir sampai persetujuan eksplisit dicatat (waktu dan versi dokumen tersimpan sebagai bukti).
- Penarikan persetujuan memicu penghentian pemrosesan dan penghapusan data dalam 3 × 24 jam. [V] (perlu verifikasi hukum)
- Pengguna menyatakan berusia ≥ 18 tahun. [A] UU PDP mewajibkan persetujuan orang tua atau wali untuk data anak. [V]

**US-07: Kuota yang jelas**
*Sebagai pengguna, saya ingin tahu batas pemakaian saya agar tidak terkejut saat ditolak.*

- Kuota harian ditampilkan di halaman unggah: sisa menit audio hari ini. Default: 60 menit per pengguna per hari, 2 job aktif bersamaan. [A] Dikalibrasi ulang dengan rumus di 3.4.5 setelah kecepatan RTX 4050 terukur.
- Melebihi kuota menghasilkan pesan jelas dan waktu reset (UTC+7, tengah malam).
- Menit audio pada job dengan pelabelan pembicara dihitung 2× terhadap kuota sampai biayanya terukur. [A]

**US-08: Pelabelan pembicara**
*Sebagai pengguna, saya ingin tahu siapa yang berbicara di setiap bagian rekaman agar wawancara dan rapat mudah dibaca dan dikutip.*

- Saat mengunggah, pengguna dapat mengaktifkan "Pisahkan pembicara". Default mati, dengan keterangan bahwa proses menjadi lebih lama dan memakai 2× kuota. [A]
- Pengguna dapat memberi petunjuk jumlah pembicara (minimum dan maksimum). Maksimum yang didukung adalah 8. [A]
- Hasil menampilkan label "Pembicara 1" sampai "Pembicara N" pada setiap segmen.
- Pengguna dapat mengganti nama label (misalnya "Pembicara 1" menjadi "Dina"). Perubahan berlaku untuk semua segmen berlabel itu dan tersimpan.
- Pengguna dapat memindahkan satu segmen ke pembicara lain untuk mengoreksi kesalahan.
- Ekspor mengikuti nama pembicara: TXT dan DOCX menampilkan nama sebelum teks, SRT dan VTT memakai awalan "Nama:".
- Label hanya berlaku di dalam satu transkrip. Sistem tidak mengenali orang yang sama pada rekaman berbeda dan tidak menyimpan sidik suara.
- Bila pelabelan gagal, transkrip tetap diterima tanpa label disertai pemberitahuan, dan kuota tambahan dikembalikan.
- Pemberitahuan privasi menyebut bahwa ciri suara diproses sementara untuk pelabelan dan tidak disimpan.

### 2.4 Ringkasan Batas Pemakaian (Awal)

| Parameter | Nilai | Status |
|---|---|---|
| Ukuran berkas maksimum | 200 MB | [A] |
| Durasi berkas maksimum | 90 menit | [A] |
| Kuota harian per pengguna | 60 menit audio | [A] |
| Job aktif bersamaan per pengguna | 2 | [A] |
| Retensi audio | ≤ 24 jam setelah job selesai, gagal, atau kedaluwarsa | [A] |
| Kedaluwarsa job yang menunggu pekerja | 72 jam | [A] |
| Retensi transkrip | 30 hari | [A] |
| Pelabelan pembicara | Opsional, default mati, dihitung 2× kuota, maksimum 8 pembicara | [A] |
| Skala pilot | ≤ 50 pengguna undangan (pilot tertutup) | [A] |

Angka-angka ini harus disesuaikan setelah kapasitas perangkat keras terukur ([T], lihat Pertanyaan Terbuka).

### 2.5 Non-Goals (Tidak Dibangun pada Rilis Ini)

- Transkripsi langsung (live streaming) dan dikte ke aplikasi lain. Whisper bukan model streaming dan membutuhkan logika potongan tambahan. [V]
- Pengenalan pembicara lintas rekaman (mengenali siapa orangnya dari sidik suara tersimpan). Data biometrik termasuk data pribadi spesifik menurut UU PDP Pasal 4 ayat (2) huruf b. [V] Paling cepat v2.0, setelah DPIA dan persetujuan terpisah. Pelabelan pembicara di dalam satu rekaman termasuk lingkup (US-08).
- Terjemahan antarbahasa.
- Pembayaran, paket berlangganan, atau penagihan.
- Aplikasi seluler asli dan API publik.
- Fitur tim atau berbagi dokumen antarpengguna.
- Pengambilan audio dari tautan (YouTube dan sejenisnya). Menimbulkan risiko hak cipta dan beban tambahan. [A]
- Pelatihan ulang model dari data pengguna. Audio pengguna tidak dipakai untuk melatih model apa pun. [A]

---

## 3. Persyaratan Sistem AI

### 3.1 Model dan Runtime

| Parameter | Keputusan | Status |
|---|---|---|
| Model utama | Whisper large-v3-turbo (±809 juta parameter) | [V] spesifikasi; pilihan pemilik produk |
| Model cadangan | Whisper large-v3 penuh, kuantisasi int8, dipakai bila model utama gagal memenuhi K1 (lihat 3.4.8) | [A] |
| Runtime | faster-whisper (CTranslate2), `compute_type` `int8_float16` sebagai titik awal; fp16 dibandingkan pada benchmark. Laptop memakai Windows asli (D-16). WSL2 menjadi cadangan, lalu whisper.cpp, bila pemasangan CUDA bermasalah. | [A] kandidat; pemenang diputuskan benchmark [T] |
| Anggaran VRAM | Turbo: ±1,5 GB (int8) dan ±2,5 GB (fp16) pada benchmark LibriSpeech faster-whisper. Large-v3: ±3 sampai 4 GB (int8) dan ±4,5 GB (fp16). Pada GPU 6 GB hanya satu model besar dimuat sekaligus. VRAM bebas aktual lebih kecil dari 6 GB karena dipakai sistem dan layar. | [V] angka bervariasi menurut sumber dan pengaturan; VRAM bebas aktual [T] |
| Konkurensi | 1 job per waktu pada GPU. Pembagian audio menjadi batch di dalam satu job diperbolehkan. Pada GPU laptop 6 GB, batch 10 sekitar 2,5× lebih cepat daripada sekuensial (audio Prancis, int8); efek pada bahasa Indonesia diukur sendiri. | [V] untuk Prancis; Indonesia [T] |
| Bahasa | `language="id"` sebagai default. Pilihan `en`. Deteksi otomatis hanya bila dipilih pengguna. | [A] |
| Versi | Revisi model dan versi pustaka dipatok dan dicatat di setiap transkrip. | [A] |
| Model diarisasi | `pyannote/speaker-diarization-community-1` (lisensi CC-BY-4.0, perlu persetujuan syarat dan token Hugging Face untuk mengunduh). Keluaran `exclusive_speaker_diarization` dipakai karena disebut mempermudah penyelarasan dengan penanda waktu transkripsi. | [V] lisensi dan keluaran; kecocokan untuk bahasa Indonesia [T] |
| Urutan GPU | Per job: Whisper dijalankan lebih dulu, dimuat keluar dari VRAM, lalu diarisasi dijalankan, lalu hasil digabung. Dua model tidak dimuat bersamaan pada 6 GB. | [A] dibuktikan pada spike TK-050 |
| Cadangan diarisasi | Bila community-1 gagal memenuhi K6 atau tidak muat di GPU, kandidat berikutnya adalah `diarize` (Apache 2.0, CPU) yang melaporkan DER sekitar 10,8% pada VoxConverse. | [V] angka dari README paket, satu dataset; Indonesia [T] |

Catatan risiko: satu sumber vendor menyebut turbo menurun lebih tajam daripada large-v3 pada bahasa sumber daya rendah. Ini diperlakukan sebagai hipotesis yang diuji pada set uji, bukan sebagai fakta. [A]

### 3.2 Persyaratan Pipeline Pemrosesan

| ID | Persyaratan | Status |
|---|---|---|
| AI-01 | **Validasi masukan.** `ffprobe` memeriksa kontainer, durasi, dan keberadaan aliran audio sebelum dekode. Berkas tanpa aliran audio atau melebihi 90 menit ditolak. `ffmpeg` berjalan dengan batas waktu 10 menit, tanpa akses jaringan (`-protocol_whitelist file,pipe`), dan tanpa hak istimewa. | [A] |
| AI-02 | **Normalisasi audio.** Semua masukan diubah ke WAV PCM 16 kHz mono sebelum inferensi. | [A] |
| AI-03 | **Deteksi ucapan (VAD).** Memakai Silero VAD bawaan faster-whisper (`vad_filter=True`). Nilai `min_silence_duration_ms` dikalibrasi pada set uji. | [A] nilai [T] |
| AI-04 | **Parameter dekode.** Titik awal: `beam_size=5`, temperature fallback aktif, `condition_on_previous_text=False` untuk menekan pengulangan. Parameter final ditetapkan benchmark. | [A] |
| AI-05 | **Anti-halusinasi dan anti-pengulangan.** Segmen dibuang bila peluang tanpa ucapan tinggi dan log-probabilitas rata-rata rendah (ambang dikalibrasi). Segmen dengan n-gram sama berulang > 5 kali berturut-turut dikodekan ulang sekali pada temperatur lebih tinggi. Bila masih berulang, segmen ditandai "[tidak jelas]". | [A] ambang [T] |
| AI-06 | **Keluaran.** Setiap segmen berisi waktu mulai dan selesai (detik), teks, dan skor keyakinan. Segmen dengan keyakinan di bawah ambang ditandai di antarmuka agar pengguna meninjaunya (mendukung US-03). | [A] |
| AI-07 | **Kegagalan GPU.** Jika memori GPU habis, job dicoba ulang sekali dengan ukuran batch setengahnya. Jika gagal lagi, status "gagal (kapasitas)" dengan pesan yang bisa dipahami. Tidak ada cadangan CPU otomatis pada MVP karena kecepatan CPU laptop belum terukur. | [A] kecepatan CPU [T] |
| AI-08 | **Perlindungan laptop.** Pekerja tidak mengambil job baru bila baterai < 30% dan tidak dicas, atau bila suhu GPU melewati ambang. Selama job berjalan, pekerja mencegah laptop masuk mode tidur. | [A] ambang suhu [T] |
| AI-09 | **Pemulihan job terputus.** Job yang pekerjanya berhenti mengirim detak > 5 menit dikembalikan ke antrean dan diproses ulang dari awal. Maksimal 3 percobaan, lalu status gagal. | [A] |
| AI-10 | **Tidak ada jejak data di laptop.** Berkas kerja dihapus segera setelah job selesai atau gagal. Log laptop tidak memuat teks transkrip atau nama berkas pengguna. Audio dan teks pengguna tidak dikirim ke layanan AI pihak ketiga dan tidak dipakai untuk melatih model. | [A] |
| AI-11 | **Diarisasi.** Bila pengguna mengaktifkan "Pisahkan pembicara", setelah transkripsi selesai pekerja membebaskan VRAM Whisper, menjalankan `pyannote` community-1 pada audio WAV 16 kHz yang sama, dengan `min_speakers` dan `max_speakers` dari petunjuk pengguna (maksimum 8). | [A] |
| AI-12 | **Penggabungan.** Setiap segmen transkrip diberi pembicara yang giliran bicaranya paling banyak beririsan dengan segmen itu. Segmen tanpa irisan memakai pembicara segmen sebelumnya. Pada MVP penggabungan berbasis segmen. Pemecahan di tengah segmen memakai penanda waktu kata (`word_timestamps`) dan masuk v1.1. | [A] |
| AI-13 | **Kegagalan diarisasi.** Bila diarisasi gagal (OOM, galat model), job tetap selesai tanpa label, ditandai "label pembicara tidak tersedia", dan kuota tambahan dikembalikan (US-08). | [A] |
| AI-14 | **Tanpa sidik suara tersimpan.** Embedding suara hanya ada di memori proses dan dibuang saat job selesai. Label bersifat anonim ("Pembicara N") dan hanya berlaku di dalam satu job. | [A] |

### 3.3 Kebutuhan Alat

| Alat | Fungsi | Status |
|---|---|---|
| faster-whisper, CTranslate2, CUDA dan cuDNN | Inferensi pada GPU RTX 4050 | [T] versi dipatok setelah pemasangan di Windows asli lolos uji (D-16) |
| `ffmpeg`, `ffprobe` | Validasi dan konversi audio | [A] |
| Silero VAD (bawaan faster-whisper) | Pemotongan bagian tanpa ucapan | [A] |
| `jiwer` | Perhitungan WER dan CER | [A] |
| `k6` | Uji beban API di VPS | [A] |
| `nvidia-smi` | Pencatatan VRAM, suhu, dan daya selama benchmark dan produksi | [A] |
| `pyannote.audio`, PyTorch dengan CUDA | Pelabelan pembicara | [A] versi dipatok setelah spike. Satu sumber menyebut dukungan diarisasi hanya sampai Python 3.13 [V, lemah] |
| `pyannote.metrics` | Perhitungan DER (K6) | [A] |
| Token Hugging Face (baca) | Mengunduh model diarisasi sekali, lalu tembolok lokal. Token tidak boleh masuk repositori. | [A] |
| Antarmuka pekerja dan VPS (ambil job, kirim detak, kirim hasil) | Dirinci di Bagian 4 | [T] |
| LLM atau API AI pihak ketiga | **Tidak dipakai** pada MVP | [A] |

### 3.4 Strategi Evaluasi

**3.4.1 Set uji.** 60 klip × 1 menit, 5 kategori × 12 klip: wawancara, rapat, pesan suara WhatsApp, audio berderau, dan campur Indonesia-Inggris. Sumber utama: rekaman sendiri dengan persetujuan tertulis semua pembicara. Pembanding eksternal: set publik bahasa Indonesia (misalnya Common Voice dan FLEURS) setelah keberadaan subset, kualitas, dan lisensinya diverifikasi. [T] Audio pengguna produksi tidak boleh dipakai sebagai set uji tanpa persetujuan terpisah. Set uji dibekukan sebelum benchmark dan tidak diubah setelah melihat hasil.

**3.4.2 Transkrip acuan.** Dibuat oleh 2 penyunting independen. WER antar-penyunting dihitung. Bila > 5%, pedoman anotasi diperbaiki dan klip dianotasi ulang, lalu perbedaan direkonsiliasi. [A]

**3.4.3 Normalisasi sebelum skor.** Huruf kecil, tanda baca dibuang, kata pengisi (eh, hmm) diabaikan. Kata tidak baku dipertahankan seperti diucapkan (misalnya "nggak", "udah") dan kata serapan Inggris tetap berhuruf asli. Dua skor dilaporkan: **WER ketat** (tanpa pemetaan) dan **WER longgar** (dengan daftar pemetaan varian ejaan umum). K1 memakai WER longgar. Daftar pemetaan dibekukan dan diberi versi sebelum pengujian agar tidak disesuaikan setelah melihat hasil. [A]

**3.4.4 Metrik dan ambang lulus.**

| Metrik | Ambang lulus | Status |
|---|---|---|
| WER longgar keseluruhan | ≤ 15% (K1) | [A] |
| WER longgar per kategori | Dilaporkan semua. Kategori > 30% dicatat sebagai keterbatasan di pemberitahuan kepada pengguna. | [A] |
| Halusinasi pada audio tanpa ucapan | ≥ 95% dari 20 klip hening atau derau murni menghasilkan keluaran kosong (≤ 2 kata) | [A] |
| Pengulangan | 0 transkrip dengan n-gram sama berulang > 5 kali berturut-turut pada set uji | [A] |
| Ketepatan penanda waktu | ≥ 95% dari 100 segmen sampel mulai dalam ±1 detik dari waktu sebenarnya (diperiksa manual) | [A] |
| Kecepatan (xRT = durasi audio ÷ waktu proses) | ≥ 8× berkelanjutan untuk file 60 menit pada daya listrik, 3 kali ulang, laporkan median dan terburuk. K2 membutuhkan ≥ 4×, sisanya cadangan antrean. | [A] ambang; nilai [T] |
| VRAM puncak | ≤ 5 GB | [A] |
| Konsistensi | Dua kali proses pada masukan sama berselisih ≤ 0,5 poin WER | [A] |
| DER pelabelan pembicara (K6) | ≤ 25% (collar 0,25 s) pada 20 klip multi-pembicara | [A] |
| Akurasi jumlah pembicara | ≥ 75% klip dengan jumlah pembicara terdeteksi sama persis, dan ≥ 90% dalam selisih ±1 | [A] |
| xRT dengan pelabelan | ≥ 3× berkelanjutan untuk file 60 menit. K2 dengan pelabelan membutuhkan ≥ 1,7×. | [A] ambang; nilai [T] |
| VRAM puncak dengan diarisasi | ≤ 5 GB pada tahap mana pun (tahap tidak bersamaan) | [A] |

**3.4.5 Rumus kapasitas dan kuota.**
Kapasitas harian (menit audio) = jam layanan per hari × 60 × xRT × faktor pemanfaatan (0,6 [A]).
Contoh ilustratif, bukan target: jam layanan 6, xRT 8 → 6 × 60 × 8 × 0,6 = 1.728 menit audio per hari.
Kuota harian per pengguna dan jumlah pengguna undangan ditetapkan dari rumus ini setelah xRT dan jam layanan nyata diketahui. [T]

**3.4.6 Uji regresi.** Setiap penggantian model, versi pustaka, atau parameter dekode menjalankan ulang seluruh set uji. Perubahan ditolak bila WER longgar naik > 1,0 poin absolut atau metrik halusinasi dan pengulangan memburuk. Hasil disimpan per versi di repositori. [A]

**3.4.7 Pemantauan produksi tanpa menyimpan teks.** Dicatat per job: xRT, status, proporsi segmen berkeyakinan rendah, dan rasio penyuntingan (karakter yang diubah ÷ total karakter). Teks sunting tidak disimpan untuk analisis atau pelatihan. Pengumpulan metrik ini diungkapkan di pemberitahuan privasi. Sinyal awal: median rasio penyuntingan ≤ 15%. [A]

**3.4.8 Pintu keputusan model.**

1. Bila turbo memenuhi K1 → tetap memakai turbo.
2. Bila turbo > 15% tetapi large-v3 int8 ≤ 15% dan xRT large-v3 ≥ 4× → pindah ke large-v3 dan kuota dihitung ulang.
3. Bila keduanya > 15% → pemilik produk memutuskan antara menaikkan ambang secara terbuka di pemberitahuan atau mengevaluasi model lain. Keputusan dicatat di Lampiran A.

**3.4.9 Evaluasi pelabelan pembicara.**

1. Set uji khusus: 20 klip × 3 sampai 5 menit dengan 2 sampai 5 pembicara (wawancara dua orang, rapat, diskusi kelompok), rekaman sendiri dengan persetujuan semua pembicara. Dibekukan sebelum benchmark. [A]
2. Anotasi giliran bicara oleh 2 penyunting independen. Selisih antar-penyunting (DER di antara keduanya) dilaporkan sebagai batas bawah yang realistis. [A]
3. DER dihitung dengan `pyannote.metrics` (collar 0,25 s). Dilaporkan juga per jumlah pembicara dan per tingkat tumpang tindih ucapan, karena ucapan tumpang tindih dan giliran sangat pendek adalah sumber galat utama diarisasi. [V] untuk sifat galat; angka Indonesia [T]
4. Pintu keputusan: bila DER > 25% pada community-1, evaluasi kandidat cadangan (3.1). Bila semuanya > 25%, fitur dirilis dengan label "eksperimental" di antarmuka dan K6 dicatat sebagai keterbatasan terbuka (Lampiran A).
5. Regresi (3.4.6) berlaku juga untuk model diarisasi dan parameternya.

### 3.5 Di Luar Lingkup AI pada MVP

Tidak ada peringkasan atau penulisan ulang teks oleh LLM, identifikasi pembicara lintas rekaman (pelabelan dalam satu rekaman termasuk lingkup, lihat US-08), terjemahan, kloning suara, maupun penyempurnaan model (fine-tuning). [A]

## 4. Spesifikasi Teknis

### 4.1 Arsitektur

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

| Komponen | Peran | Catatan |
|---|---|---|
| Cloudflare Pages | Menyajikan antarmuka web statis | Paket gratis. Tanpa Workers pada MVP, jadi batas 100.000 permintaan/hari dan 10 ms CPU tidak berlaku. [A] |
| Cloudflare proksi, WAF, Turnstile | Perlindungan DNS, pembatasan dasar, anti-bot | Paket gratis. Badan permintaan ke VPS tetap < 100 MB karena audio tidak lewat sini. [V] |
| Cloudflare R2 | Penyimpanan audio sementara | Privat. Unggah dan unduh lewat URL bertanda tangan ke domain S3, bukan domain kustom. Perlu CORS di bucket. [V] |
| VPS: Caddy + FastAPI + SQLite | API, autentikasi, kuota, antrean, penjadwal retensi, ekspor | Satu proses API (2 pekerja uvicorn) dan satu proses penjadwal. |
| Laptop: pekerja | Validasi media, Whisper, diarisasi, penggabungan | Hanya koneksi keluar. Tidak menyimpan apa pun setelah job. |

### 4.2 Keputusan Teknologi

| Area | Pilihan | Alasan | Status |
|---|---|---|---|
| Bahasa API dan pekerja | Python 3.12 (dipatok setelah spike) | Satu bahasa untuk API dan pekerja, ekosistem `faster-whisper` dan `pyannote` | [A] |
| Kerangka API | FastAPI + Pydantic, OpenAPI sebagai kontrak | Jenis data tervalidasi, dokumen API otomatis, ringan di RAM 2 GB | [A] |
| Basis data | SQLite mode WAL | ≤ 50 pengguna dan satu VPS kecil. Tidak ada daemon basis data yang memakan RAM. Antrean job memakai tabel dengan sewa (lease). | [A] |
| Frontend | Vite + React + TypeScript, klien API dihasilkan dari OpenAPI | Statis, mudah dipasang di Pages | [A] |
| Klien R2 | `boto3` (S3 API) di VPS. Browser memakai `fetch` ke URL bertanda tangan. | R2 kompatibel S3 | [V] |
| Antrean | Tabel `jobs` + sewa 5 menit + detak 30 detik | Tanpa Redis, tanpa Cloudflare Queues | [A] |
| Status waktu nyata | Polling tiap 5 detik | Memenuhi jeda ≤ 10 detik (US-02), tanpa koneksi panjang | [A] |
| Penerapan VPS | Docker Compose atau systemd (pilih salah satu di TK-004) | Pemulihan otomatis saat reboot | [A] |
| Penerapan pekerja | Python venv di Windows, dijalankan oleh Task Scheduler saat masuk (logon) di akun Windows tanpa hak admin | Tidak butuh layanan tambahan | [A] |

### 4.3 Struktur Repositori

```
repo/
  apps/web/        Vite + React + TS (Cloudflare Pages)
  apps/api/        FastAPI, migrasi SQLite, penjadwal retensi
  apps/worker/     pekerja inferensi (Windows), CLI benchmark
  contracts/       openapi.yaml, skema JSON protokol pekerja
  eval/            set uji (di luar git bila berisi suara), skrip WER dan DER, hasil per versi
  infra/           konfigurasi Caddy, compose/systemd, wrangler (Pages), CORS dan lifecycle R2
  docs/            PRD.md, ADR/, privasi (ROPA, DPIA-lite), runbook
  TICKETS.md
```

### 4.4 Model Data (SQLite)

| Tabel | Kolom utama | Catatan |
|---|---|---|
| `users` | id, email, google_sub, status (aktif/dinonaktifkan), dibuat_pada | Hanya email yang ada di allowlist yang bisa masuk |
| `allowlist` | email, ditambahkan_pada | Dikelola pengelola lewat CLI |
| `consents` | id, user_id, versi_dokumen, diberikan_pada, ditarik_pada | Bukti persetujuan (US-06) |
| `jobs` | id, user_id, state, nama_berkas_asli, r2_key, ukuran_byte, durasi_detik, bahasa, diarisasi (0/1), min_pembicara, maks_pembicara, menit_dikenakan, percobaan, worker_id, lease_sampai, dibuat_pada, selesai_pada, audio_dihapus_pada, hapus_transkrip_pada, kode_galat, versi_model | Nama berkas disimpan hanya untuk tampilan pengguna dan tidak masuk log |
| `segments` | job_id, urut, mulai, selesai, teks, keyakinan, speaker_id, disunting (0/1), versi | Teks sunting menimpa teks asli dalam baris yang sama |
| `speakers` | job_id, speaker_id, label_asli ("Pembicara 1"), nama_tampil | Nama diubah pengguna |
| `workers` | id, nama, token_hash, terakhir_terlihat, versi | Token acak 256-bit, hanya hash yang disimpan |
| `usage_ledger` | user_id, tanggal_lokal, job_id, menit, jenis (kenakan/kembalikan) | Dasar kuota harian (UTC+7) |
| `audit_events` | waktu, user_id, jenis, job_id | Tanpa isi transkrip. Dipakai untuk bukti persetujuan, penghapusan, dan penarikan |

### 4.5 Mesin Status Job

`uploading` → `queued` → `processing` (tahap: `probing`, `transcribing`, `diarizing`, `merging`) → `completed`

Cabang: `failed` (kode galat dan pesan manusiawi), `expired` (menunggu pekerja > 72 jam), `cancelled` (pengguna menghapus), `deleted` (audio dan transkrip sudah dihapus).

| Transisi | Pemicu |
|---|---|
| `uploading` → `queued` | Unggahan multipart selesai dan pemeriksaan ringan lolos |
| `queued` → `processing` | Pekerja mengambil job dan mendapat sewa |
| `processing` → `queued` | Sewa habis (tanpa detak > 5 menit). Percobaan bertambah. Maksimal 3, lalu `failed`. |
| `processing` → `completed` / `failed` | Pekerja mengirim hasil atau galat |
| `queued` → `expired` | 72 jam tanpa diambil |
| mana saja → `cancelled` | Pengguna menghapus job |

### 4.6 Alur Unggah ke R2 (Multipart, Dapat Dilanjutkan)

1. Klien memeriksa ekstensi dan ukuran (≤ 200 MB). Durasi dari elemen media peramban dipakai hanya sebagai petunjuk kuota, bukan sebagai nilai resmi.
2. `POST /api/uploads` membawa nama berkas, ukuran, tipe konten, bahasa, opsi diarisasi, dan token Turnstile. VPS memeriksa persetujuan, kuota, jumlah job aktif, dan batas total penyimpanan, membuat baris `jobs` (`uploading`), memanggil `CreateMultipartUpload`, lalu mengembalikan `job_id`, `upload_id`, dan jumlah potongan.
3. `POST /api/uploads/{job_id}/parts` meminta URL bertanda tangan untuk nomor potongan tertentu (TTL 15 menit). Ukuran potongan 8 MiB. Setiap potongan kecuali yang terakhir harus berukuran sama, dan potongan minimal 5 MiB. [V] Klien mengunggah paling banyak 3 potongan paralel dan membaca `ETag` (perlu `ExposeHeaders: ETag` di CORS).
4. Bila koneksi putus, klien memanggil `GET /api/uploads/{job_id}` yang mengembalikan potongan yang sudah ada (`ListParts`), lalu melanjutkan.
5. `POST /api/uploads/{job_id}/complete` membawa daftar (nomor, ETag). VPS memanggil `CompleteMultipartUpload`, membaca 64 KiB pertama berkas untuk memeriksa tanda tangan, mencocokkan ukuran, lalu mengubah status menjadi `queued`.
6. Unggahan yang tidak selesai dalam 24 jam dibatalkan (`AbortMultipartUpload`) oleh penjadwal dan job dihapus. Aturan siklus hidup R2 sebagai jaring pengaman: batalkan multipart yang menggantung dan hapus objek `uploads/` yang lebih tua dari 7 hari.

Kunci objek: `uploads/{user_id}/{job_id}` tanpa nama berkas asli.

### 4.7 Antarmuka API

**Untuk pengguna** (sesi cookie `HttpOnly`, `Secure`, `SameSite=Lax`; `app.` dan `api.` berada di bawah domain terdaftar yang sama).

| Metode dan jalur | Fungsi |
|---|---|
| `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/logout` | Masuk dan keluar |
| `GET /api/me` | Profil, kuota tersisa, persetujuan terbaru |
| `POST /api/consents`, `DELETE /api/consents` | Memberi dan menarik persetujuan |
| `POST /api/uploads`, `POST /api/uploads/{id}/parts`, `GET /api/uploads/{id}`, `POST /api/uploads/{id}/complete` | Alur unggah (4.6) |
| `GET /api/jobs`, `GET /api/jobs/{id}` | Daftar dan status job, posisi antrean, perkiraan waktu |
| `DELETE /api/jobs/{id}`, `DELETE /api/me` | Hapus job, hapus seluruh akun |
| `GET /api/jobs/{id}/transcript` | Segmen dan pembicara |
| `PATCH /api/jobs/{id}/segments/{n}` | Sunting teks atau pindahkan pembicara (membawa `versi` untuk deteksi tabrakan) |
| `PATCH /api/jobs/{id}/speakers/{sid}` | Ganti nama pembicara |
| `GET /api/jobs/{id}/audio-url` | URL bertanda tangan sementara untuk pemutar (TTL 15 menit), hanya selama audio ada |
| `GET /api/jobs/{id}/export?format=txt\|srt\|vtt\|docx` | Ekspor |

**Untuk pekerja** (header `Authorization: Bearer <token pekerja>`, hanya koneksi keluar dari laptop).

| Metode dan jalur | Fungsi |
|---|---|
| `POST /worker/v1/jobs/claim?wait=25` | Pekerja meminta job berikutnya. VPS menahan permintaan hingga 25 detik bila antrean kosong. Respons: `job_id`, URL GET bertanda tangan ke R2 (TTL 15 menit), pengaturan bahasa dan diarisasi, `lease_sampai`. |
| `POST /worker/v1/jobs/{id}/heartbeat` | Tiap 30 detik. Memperpanjang sewa dan melaporkan tahap. VPS membalas `cancel: true` bila pengguna menghapus job. |
| `POST /worker/v1/jobs/{id}/result` | Segmen, pembicara, durasi, xRT, versi model, rasio segmen berkeyakinan rendah |
| `POST /worker/v1/jobs/{id}/fail` | Kode galat dan apakah boleh dicoba ulang |
| `POST /worker/v1/ping` | Pendaftaran dan pemeriksaan versi |

Pengambilan job memakai pernyataan atomik: `UPDATE jobs SET state='processing', worker_id=?, lease_sampai=? WHERE id=(SELECT id FROM jobs WHERE state='queued' ORDER BY dibuat_pada LIMIT 1) RETURNING ...`. SQLite memberi satu penulis pada satu waktu, cukup untuk skala ini. [A]

### 4.8 Pipeline pada Laptop (Urutan GPU)

1. Klaim job, unduh audio dari R2 ke direktori kerja sementara (akun Windows terbatas).
2. `ffprobe` dan `ffmpeg` (AI-01, AI-02) di dalam proses anak dengan batas waktu 10 menit dan tanpa jaringan.
3. Muat Whisper, transkripsi dengan VAD (AI-03 sampai AI-06). Kirim detak tiap 30 detik. Bebaskan model dari VRAM.
4. Bila diarisasi aktif: muat `pyannote` community-1, jalankan (AI-11), bebaskan model.
5. Gabungkan (AI-12), rakit hasil, kirim ke VPS.
6. Hapus semua berkas kerja (AI-10) dan laporkan selesai. Pada kegagalan apa pun, tetap hapus berkas kerja.

Sebelum langkah 1 pekerja memeriksa AI-08 (baterai, suhu, pencegah tidur). Waktu muat model berulang per job adalah biaya yang diukur di Fase 0. Bila besar, model Whisper boleh tetap dimuat antar-job selama tidak ada diarisasi yang berjalan. [T]

### 4.9 Autentikasi dan Anti-Penyalahgunaan

| Kontrol | Rincian | Status |
|---|---|---|
| Masuk | Google OIDC, hanya email di `allowlist`, tanpa kata sandi lokal | [A] (D-04) |
| Sesi | Cookie sesi tersandi, masa berlaku 7 hari, dicabut saat keluar | [A] |
| Turnstile | Wajib pada login dan pada `POST /api/uploads`. Token diverifikasi di VPS. | [A] |
| Pembatasan laju | Per pengguna dan per IP di API: unggah 10 inisiasi/jam, ekspor 60/jam, endpoint pekerja hanya untuk token pekerja | [A] |
| Kuota | 60 menit/hari, 2 job aktif, 2× bila diarisasi (US-07). Plafon global penyimpanan R2: tolak inisiasi unggahan bila total audio tersimpan > 8 GB. | [A] |
| Kunci asal | VPS hanya menerima lalu lintas dari rentang IP Cloudflare dan SSH dari IP pengelola | [A] |
| Rahasia | Kredensial R2, rahasia OAuth, token pekerja, dan token Hugging Face hanya di variabel lingkungan atau berkas yang izin aksesnya dibatasi. Tidak ada di repositori. | [A] |

### 4.10 Model Ancaman (STRIDE) Ringkas

| Kategori | Ancaman | Mitigasi |
|---|---|---|
| Spoofing | Pihak lain meniru pekerja atau pengguna | Token pekerja acak 256-bit dengan hash di basis data, dapat dirotasi. Login Google dengan allowlist. |
| Tampering | URL unggah dipakai untuk menimpa objek lain, atau pengguna menyunting transkrip milik orang lain | URL bertanda tangan per kunci dan per potongan, TTL pendek. Setiap kueri API difilter `user_id`. |
| Repudiation | Sengketa soal persetujuan atau penghapusan | `consents` dan `audit_events` mencatat waktu dan versi dokumen. |
| Information disclosure | Audio bocor lewat URL, log, atau disk laptop | R2 privat, URL pendek, kunci objek tanpa nama berkas, log tanpa teks atau nama berkas, berkas kerja dihapus di `finally`. |
| Denial of service | Unggahan besar atau banyak job menghabiskan GPU atau R2 | Kuota, plafon global, pembatasan laju, Turnstile, satu job per waktu. |
| Elevation of privilege | Berkas media berbahaya mengeksploitasi `ffmpeg` atau pustaka dekode di laptop | Akun Windows tanpa hak admin khusus pekerja, `ffmpeg` terbaru, tanpa jaringan, batas waktu, ukuran dan durasi dibatasi sebelum dekode, laptop tidak berisi rahasia VPS selain token pekerja. |

Risiko tersisa terbesar adalah laptop pribadi memproses berkas dari orang lain. Karena itu pilot hanya untuk undangan tepercaya. [A]

### 4.11 Privasi dan Kepatuhan (UU PDP)

Bukan nasihat hukum. Sumber hukum bersifat sekunder dan harus diverifikasi ke teks resmi (T-12).

| Topik | Rancangan | Status |
|---|---|---|
| Dasar pemrosesan | Persetujuan eksplisit sebelum unggahan pertama, versi dan waktu dicatat | [A] |
| Pengendali data | Pengembang sebagai individu (proyek kuliah). Peran kampus dan dosen belum ditetapkan (T-06). | [A] |
| ROPA dan DPIA | Dokumen ROPA ringkas dan DPIA-lite dibuat sebelum pendaftaran dibuka di luar undangan. PP 33/2026 berlaku 16 Januari 2027. [V] sumber sekunder | [A] |
| Data khusus | Pelabelan pembicara tidak menyimpan sidik suara (AI-14). Apakah ciri suara sementara tetap dihitung sebagai data biometrik perlu telaah hukum (T-12). Sistem tidak mengenali orang lintas rekaman. | [T] |
| Lintas negara | Audio berada di R2 dan VPS. Lokasi VPS belum diketahui (T-08). Pemberitahuan privasi menyebut penyedia dan negara penyimpanan. R2 mendukung petunjuk lokasi bucket, nilai dipilih di TK-003. | [T] |
| Hak subjek | Akses, salinan (ekspor), hapus, tarik persetujuan, dipenuhi ≤ 3 × 24 jam | [V] sekunder |
| Kebocoran | Prosedur pemberitahuan ≤ 3 × 24 jam ditulis di runbook | [V] sekunder |
| Anak | Deklarasi ≥ 18 tahun | [A] |
| Metrik tanpa teks | Hanya metrik agregat per job (3.4.7), diungkap di pemberitahuan | [A] |

### 4.12 Retensi dan Penghapusan

| Data | Retensi | Mekanisme |
|---|---|---|
| Audio di R2 | ≤ 24 jam setelah `completed`, `failed`, `expired`, atau `cancelled` | Penjadwal tiap 15 menit menghapus objek lalu mengisi `audio_dihapus_pada`. Jaring pengaman: lifecycle R2 7 hari. |
| Berkas kerja di laptop | Segera setelah job | Blok `finally` pekerja. Audit K4 memeriksa direktori kerja. |
| Transkrip dan segmen | 30 hari, atau lebih awal bila pengguna menghapus | Penjadwal harian. |
| Akun | Sampai pengguna menghapus | `DELETE /api/me` menghapus job, segmen, audio, dan sesi. Baris `consents` dan `audit_events` dipertahankan tanpa isi pribadi sebagai bukti. |
| Cadangan basis data | Maksimal 7 hari | Cadangan harian terenkripsi. Penghapusan baru hilang dari cadangan paling lambat 7 hari kemudian, dan hal ini diungkap di pemberitahuan privasi. |

Audit K4 harian memindai bucket R2, direktori kerja VPS, dan (lewat laporan pekerja) direktori kerja laptop. Temuan di luar retensi menjadi peringatan.

### 4.13 Kapasitas

| Sumber daya | Perkiraan | Status |
|---|---|---|
| RAM VPS | Caddy ~30 MB, API 2 pekerja ~200 sampai 300 MB, penjadwal ~60 MB. Cukup di 2 GB. Tambahkan swap 1 GB. | [A] harus diukur di TK-062 |
| Penyimpanan R2 | Gratis 10 GB, 1 juta operasi Class A, 10 juta Class B per bulan. [V] Satu unggahan 200 MB sekitar 27 operasi Class A (25 potongan + 2). Plafon aplikasi 8 GB. | [A] turunan dari angka [V] |
| GPU | 1 job per waktu. Kapasitas harian dari rumus 3.4.5 setelah xRT terukur. | [T] |
| Ukuran hasil | Transkrip 90 menit sekitar 15.000 kata, jauh di bawah 1 MB | [A] |

### 4.14 Mode Kegagalan dan Pemulihan

| Kegagalan | Deteksi | Perilaku dan target pemulihan |
|---|---|---|
| Laptop mati atau tidur | Tanpa detak 90 detik | Situs menampilkan "pemrosesan tertunda". Job tetap `queued`. Selesai ≤ 60 menit setelah pekerja kembali (K3). |
| Pekerja berhenti di tengah job | Sewa habis (5 menit) | Job kembali ke antrean, percobaan +1, maksimal 3. |
| GPU kehabisan memori | Galat CUDA OOM | Ulangi sekali dengan batch setengah, lalu `failed (kapasitas)` (AI-07). |
| Diarisasi gagal | Galat tahap `diarizing` | Selesai tanpa label dan kuota tambahan dikembalikan (AI-13). |
| VPS mati | Pemantau waktu aktif eksternal | Antarmuka statis tetap tampil dengan pesan galat. Pulih otomatis saat reboot. Target ≤ 30 menit selama jam kerja pengelola. |
| R2 tidak tersedia | Galat S3 pada presign atau unduh | Unggahan ditolak dengan pesan jelas. Pekerja mencoba lagi dengan jeda bertingkat. |
| Disk VPS penuh | Peringatan ambang 80% | Tolak unggahan baru, jalankan pembersihan. |
| Basis data rusak | `PRAGMA integrity_check` harian | Pulihkan dari cadangan harian. Kehilangan maksimal 24 jam suntingan. [A] |
| Token pekerja bocor | Anomali pemakaian atau laporan | Rotasi token, semua sewa dibatalkan. |
| Token Hugging Face dicabut | Galat unduh model | Model sudah di tembolok lokal. Hanya pemasangan ulang yang terdampak. |

### 4.15 Penerapan dan Observabilitas

- Antarmuka: penerapan otomatis dari cabang `main` ke Pages. Pratinjau per cabang.
- VPS: penerapan manual terskrip (`make deploy`) dengan migrasi basis data berversi. Rollback ke gambar atau rilis sebelumnya.
- Pekerja: pembaruan dengan `git pull` dan pemasangan versi dipatok. Pekerja melaporkan versi lewat `ping` dan VPS menolak versi yang terlalu lama.
- Log terstruktur JSON tanpa nama berkas dan tanpa teks transkrip. `GET /healthz` untuk pemantau waktu aktif.
- Dasbor sederhana (halaman admin atau skrip): jumlah job per status, median xRT, tingkat gagal, panjang antrean, status pekerja, penyimpanan R2 terpakai.

---

## 5. Risiko dan Peta Jalan

### 5.1 Peta Jalan (Berdasarkan Kriteria Keluar, Tanpa Tanggal)

| Fase | Isi | Kriteria keluar |
|---|---|---|
| **Fase 0: Fondasi dan benchmark** | Scaffold repositori, kontrak API, lingkungan lokal, pemasangan CUDA di Windows, harness benchmark, set uji 60 klip, WER, spike diarisasi | xRT dan VRAM RTX 4050 terukur. Keputusan model per 3.4.8 tercatat. Pemasangan `pyannote` di Windows terbukti atau jalur WSL2 dipilih. |
| **Fase 1: MVP transkripsi (pilot tertutup)** | Login, persetujuan, unggah R2, antrean, pekerja, penyuntingan, ekspor, hapus data, kuota, retensi otomatis | K1, K2 (tanpa pelabelan), K3, K4, K5 terpenuhi pada pilot ≤ 10 pengguna undangan. Pemberitahuan privasi, ROPA, dan DPIA-lite selesai. |
| **Fase 2: Pelabelan pembicara (v1.1)** | US-08 penuh, penggabungan berbasis kata, set uji ≥ 3 jam, set multi-pembicara 20 klip | K6 terpenuhi atau fitur diberi label eksperimental dengan keputusan tercatat. K2 dengan pelabelan terpenuhi. |
| **Fase 3: Perluasan (v2.0, opsional)** | Pendaftaran lebih terbuka, pengenalan pembicara lintas rekaman, antrean prioritas | Telaah hukum dan DPIA lengkap selesai. Persetujuan terpisah untuk data biometrik. Kapasitas GPU atau tempat inferensi pengganti ditetapkan. |

Fase 0 dan Fase 1 dapat berjalan paralel pada jalur yang tidak saling bergantung (lihat `TICKETS.md`).

### 5.2 Daftar Risiko

| ID | Risiko | Jenis | Dampak | Mitigasi |
|---|---|---|---|---|
| R-01 | WER bahasa Indonesia turbo lebih tinggi dari 15% | Teknis | Tinggi | Benchmark dini di Fase 0, pintu keputusan 3.4.8, cadangan large-v3 int8 |
| R-02 | `pyannote` sulit dipasang di Windows asli atau tidak muat di GPU | Teknis | Sedang | Spike TK-050, jalur WSL2, kandidat `diarize` (CPU) |
| R-03 | DER pada bahasa Indonesia di atas 25% | Teknis | Sedang | Label eksperimental, petunjuk jumlah pembicara, penyuntingan manual (pindah segmen) |
| R-04 | Laptop sering mati sehingga antrean menumpuk | Operasional | Sedang | Pesan status jelas, kedaluwarsa 72 jam, jam layanan diumumkan |
| R-05 | Laptop terkena media berbahaya | Keamanan | Tinggi | Akun terbatas, validasi sebelum dekode, pilot undangan tepercaya |
| R-06 | Panas atau baterai merusak laptop atau menurunkan kecepatan | Operasional | Sedang | AI-08, batas suhu, pantauan `nvidia-smi` |
| R-07 | Batas gratis R2 atau Cloudflare berubah atau terlampaui | Biaya | Rendah | Plafon 8 GB, pemantauan penggunaan, tinjau ulang ketentuan |
| R-08 | Klausul Cloudflare soal penyajian berkas besar | Kepatuhan | Sedang | Audio tidak disajikan lewat proksi, hanya lewat URL bertanda tangan R2. Teks klausul dibaca penuh (T-13). |
| R-09 | Kewajiban UU PDP atau aturan kampus belum jelas | Hukum | Tinggi | Pilot tertutup, DPIA-lite, verifikasi teks resmi (T-12), beri tahu dosen pembimbing |
| R-10 | VPS 2 GB kehabisan RAM | Teknis | Sedang | Swap, pembatasan jumlah pekerja uvicorn, pemantauan, tanpa pekerjaan berat di VPS |
| R-11 | Data pengguna bocor lewat log atau cadangan | Privasi | Tinggi | Log tanpa data pribadi, cadangan ≤ 7 hari dan terenkripsi, audit K4 |
| R-12 | Persyaratan lisensi model (atribusi CC-BY, persetujuan Hugging Face) terlewat | Kepatuhan | Rendah | Halaman atribusi di situs, catat di docs |

---

## Lampiran A. Log Keputusan

| ID | Keputusan | Alasan | Status |
|---|---|---|---|
| D-01 | Model: Whisper large-v3-turbo (±809 juta parameter, decoder 4 lapis dari 32 pada large-v3) | Permintaan pemilik produk. Lebih cepat dan hemat VRAM daripada large-v3. | [V] spesifikasi, [A] kecukupan untuk bahasa Indonesia |
| D-02 | Cakupan: berkas unggahan (batch), bukan streaming | Whisper tidak streaming. Menyederhanakan MVP. | [A] |
| D-03 | Laptop hanya sebagai pekerja inferensi, tanpa port masuk. Pekerja menarik job dari VPS lewat koneksi keluar berotorisasi. | Mengurangi permukaan serangan, tidak perlu Tunnel, dan situs tetap hidup saat laptop mati. | [A], dirinci di 4.7 dan 4.8 |
| D-04 | Masuk dengan akun Google dan daftar undangan (allowlist) selama pilot. Pendaftaran terbuka hanya setelah DPIA dan tinjauan hukum/kampus selesai. | Mengurangi akun palsu dan beban GPU, serta menekan risiko hukum pada data suara. | [A] |
| D-05 | Hanya pengguna ≥ 18 tahun (deklarasi) | Data anak membutuhkan persetujuan orang tua menurut UU PDP. | [A], perlu telaah hukum |
| D-06 | Tidak ada pembayaran, kuota harian per pengguna | Menjaga kapasitas satu GPU laptop 6 GB dan biaya tambahan Rp0. | [A] |
| D-07 | Audio dihapus ≤ 24 jam, transkrip 30 hari | Meminimalkan data (prinsip minimisasi) sambil memberi waktu menyunting. | [A], jawaban T-03 |
| D-08 | Bahasa dokumen dan antarmuka: Indonesia | Target pengguna individu Indonesia. | [A] |
| D-09 | Runtime faster-whisper dengan int8_float16 sebagai titik awal | Turbo int8 ±1,5 GB VRAM, muat di 6 GB dengan ruang batch. | [V] VRAM, [A] pilihan, benchmark memutuskan |
| D-10 | Satu job per waktu pada GPU, tanpa cadangan CPU pada MVP | GPU 6 GB dan kecepatan CPU belum terukur. | [A] |
| D-11 | Tanpa LLM atau layanan AI pihak ketiga pada MVP | Audio tidak keluar dari VPS, R2, dan laptop, menyederhanakan DPIA. | [A] |
| D-12 | K1 memakai WER longgar dengan daftar pemetaan dibekukan sebelum uji | Ejaan bahasa Indonesia informal sangat bervariasi, dan pembekuan mencegah penyetelan setelah melihat hasil. | [A] |
| D-13 | Audio disimpan sementara di Cloudflare R2 lewat unggahan multipart bertanda tangan, bukan lewat VPS | Batas 100 MB badan permintaan di proksi, VPS 2 GB RAM, dan pembatasan CDN untuk berkas besar yang disajikan lewat proksi. | [V] batas, [A] pilihan |
| D-14 | VPS: FastAPI + SQLite (WAL) + Caddy, antrean berbasis tabel dengan sewa | RAM 2 GB, ≤ 50 pengguna, tanpa daemon tambahan. | [A] |
| D-15 | Pelabelan pembicara dengan `pyannote` community-1 setelah Whisper, berurutan di GPU yang sama | Dua model tidak muat bersamaan dengan aman di 6 GB. Lisensi CC-BY-4.0. | [V] lisensi, [A] urutan |
| D-16 | Pekerja berjalan di Windows asli (Python + CUDA), WSL2 sebagai cadangan | Jawaban T-07. | [A], diuji di Fase 0 |
| D-17 | Tanpa sidik suara tersimpan dan tanpa pengenalan lintas rekaman | Menghindari data biometrik tersimpan (UU PDP Pasal 4 ayat 2 huruf b). | [A], perlu telaah hukum |
| D-18 | Pemeriksaan media penuh dilakukan oleh pekerja, VPS hanya pemeriksaan ringan | VPS kecil dan tidak boleh mengurai media tak tepercaya secara berat. | [A] |
| D-19 | Tanpa tenggat. Jadwal berdasarkan kriteria keluar fase. | Jawaban T-09. | [A] |
| D-20 | Audio hanya dapat diputar selama masih tersimpan (≤ 24 jam setelah selesai) | Konsekuensi langsung dari retensi D-07. | [A] |

## Lampiran B. Pertanyaan Terbuka

| ID | Pertanyaan | Dampak |
|---|---|---|
| T-01 | **Terjawab:** laptop RTX 4050 6 GB. Sisa [T]: nilai xRT terukur, VRAM bebas aktual, perilaku termal | Kecepatan K2, kuota (3.4.4, 3.4.5) |
| T-02 | **Terjawab sementara oleh penulis:** pilot undangan dengan akun Google (D-04) | Beban kapasitas, risiko penyalahgunaan |
| T-03 | Kebijakan retensi final (sementara: audio ≤ 24 jam, transkrip 30 hari) | Bagian 4 dan kepatuhan UU PDP, perlu tinjauan hukum |
| T-04 | **Terjawab:** job antre sampai laptop aktif, kedaluwarsa 72 jam; VPS menjaga situs tetap hidup | Ketersediaan, K3 |
| T-05 | Nama produk dan subdomain | Pemberitahuan privasi dan identitas |
| T-06 | **Terjawab sebagian:** proyek kuliah, tidak ada aturan kampus tertulis, hanya penilaian dosen. Pengendali data sementara dianggap pengembang. Sisa [T]: perlu tidaknya memberi tahu dosen pembimbing dan persetujuan etik untuk data suara peserta | Kewajiban DPO, ROPA, DPIA, kelayakan pilot |
| T-07 | **Terjawab:** Windows asli (Python + CUDA). Sisa [T]: versi CUDA, cuDNN, PyTorch, dan Python yang lolos uji | Pemasangan CUDA, runtime, pencegahan tidur |
| T-08 | **Terjawab sebagian:** VPS 2 vCPU dan 2 GB RAM. Sisa [T]: disk, penyedia, dan negara VPS | Penyimpanan sementara, transfer lintas negara |
| T-09 | **Terjawab:** tidak ada tenggat (D-19) | Jadwal fase di Bagian 5 |
| T-10 | Nilai ambang dan kualitas diarisasi untuk bahasa Indonesia: apakah community-1 memenuhi K6? | K6, kelayakan fitur US-08 |
| T-11 | Apakah `pyannote.audio` dan `faster-whisper` berjalan stabil bersama di Windows asli dengan versi CUDA yang sama? | R-02, D-16 |
| T-12 | Verifikasi hukum ke teks resmi: DPO, ROPA, DPIA, status data suara dan ciri suara sementara, transfer lintas negara, periode 3 × 24 jam | Bagian 4.11, kelayakan pilot |
| T-13 | Teks lengkap Service-Specific Terms Cloudflare untuk R2 dan penyajian berkas besar | R-08, D-13 |
| T-14 | Nama produk, subdomain, dan domain terdaftar (turunan T-05) | TK-003, pemberitahuan privasi |

## Lampiran C. Sumber (diakses 2 November 2026)

**Model dan performa**

- Spesifikasi large-v3-turbo (809 M parameter, 4 lapis decoder): https://gigagpu.com/?p=12168 dan https://dev.classmethod.jp/articles/openai-whisper-large-v3-turbo-faster-whisper/
- Benchmark faster-whisper (LibriSpeech, bahasa Inggris; VRAM int8 ±1,5 GB): https://github.com/SYSTRAN/faster-whisper/issues/1030
- VRAM large-v3 (int8 ±3 sampai 4 GB, fp16 ±4,5 GB): https://www.spheron.network/blog/faster-whisper-gpu-cloud-production-deployment-guide/ dan https://vexascribe.com/faster-whisper (angka antar-sumber berbeda).
- Perbandingan batch vs sekuensial pada GPU laptop 6 GB (audio Prancis, int8): https://whispernotes.app/es-MX/blog/introducing-whisper-large-v3-turbo
- Klaim turbo lebih lemah pada bahasa sumber daya rendah (blog vendor GPU, dipakai hanya sebagai hipotesis): https://gigagpu.com/?p=34643
- Catatan: tidak ditemukan sumber tepercaya yang memberi WER bahasa Indonesia untuk large-v3-turbo. Angka itu harus diukur sendiri (K1). Klaim kecepatan dari blog vendor GPU bervariasi lebar dan tidak dipakai sebagai target.

**Diarisasi pembicara**

- pyannote community-1 (CC-BY-4.0, keluaran `exclusive_speaker_diarization`, perlu token Hugging Face dan persetujuan syarat): https://www.ssdnodes.com/learn/speaker-diarization-on-a-vps dan https://thegtmdirectory.com/models/pyannote-speaker-diarization-community/speaker-diarization-community-1
- Perbandingan DER pada VoxConverse (community-1 sekitar 11,2%, `diarize` sekitar 10,8%, satu dataset, bukan bahasa Indonesia): https://pypi.org/project/diarize/
- Ikhtisar model diarisasi 2026: https://www.pyannote.ai/blog/top-7-speaker-diarization-apis-and-models-in-2026 dan https://brasstranscripts.com/blog/speaker-diarization-models-comparison
- Catatan dukungan Python untuk ekstra diarisasi (sampai 3.13): https://pypi.org/project/vtt-transcribe/ (sumber lemah, verifikasi saat pemasangan).
- Catatan: tidak ada sumber yang memberi DER bahasa Indonesia. Angka literatur (sekitar 11 sampai 20%) dari benchmark non-Indonesia dan hanya dipakai sebagai acuan ambang awal K6.

**Cloudflare**

- Batas Workers: https://developers.cloudflare.com/workers/about/limits
- Harga dan batas gratis Workers: https://developers.cloudflare.com/workers/platform/pricing/
- Batas ukuran badan permintaan 100 MB (Free): https://developers.cloudflare.com/workers/about/limits (bagian request body)
- Batas R2 dan harga (10 GB, 1 juta Class A, 10 juta Class B gratis; multipart 5 MiB sampai 5 GiB per potongan, maksimal 10.000 potongan; URL bertanda tangan hanya untuk domain S3, perlu CORS): https://developers.cloudflare.com/r2/platform/limits/ dan https://developers.cloudflare.com/r2/platform/pricing/ (diringkas juga di https://skills.sh/itechmeat/llm-code/cloudflare-r2, sumber sekunder)
- Batas gratis D1, Queues (10.000 operasi/hari): https://workers.cloudflare.com/pricing/.md dan https://freetier.co/cloudflare-free-tier
- Pembaruan ketentuan layanan (pembatasan CDN untuk video dan berkas besar): https://blog.cloudflare.com/updated-tos/

**Hukum (sumber sekunder, belum diverifikasi ke teks resmi dan bukan nasihat hukum)**

- UU 27/2022: https://pasal.id/akn/id/act/uu/2022/27 dan Pasal 4 (data pribadi spesifik, termasuk biometrik): https://pasal.id/peraturan/uu/uu-no-27-tahun-2022/pasal-4
- Pemberitahuan kebocoran 3 × 24 jam (Pasal 46) dan persetujuan orang tua untuk data anak (Pasal 25): https://www.hukumonline.com/klinik/a/perbedaan-pengendali-dan-prosesor-data-pribadi-menurut-uu-pdp-lt636d1861766bc
- PP 33/2026 (berlaku 16 Januari 2027; DPIA, ROPA, hak subjek 3 × 24 jam, denda hingga 2% pendapatan tahunan): https://siplawfirm.id/resources/pp-33-2026-pelindungan-data-pribadi
