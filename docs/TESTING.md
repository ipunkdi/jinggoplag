# Strategi & Metodologi Pengujian

Proyek ini menggunakan dua lapis pengujian yang saling melengkapi: **pengujian otomatis** (`pytest`/`unittest`-style) untuk lapisan logika/algoritma, dan **pengujian *black-box*** untuk lapisan antarmuka pengguna.

## 1. Pengujian Otomatis (`tests/test_parity.py`)

### Mengapa Disebut "Parity"?

Nama *parity* (kesetaraan) dipilih karena tujuan utama *test suite* ini bukan sekadar memeriksa "kode tidak *crash*", melainkan memverifikasi **kesetaraan numerik** antara hasil komputasi sistem dan *ground truth* yang dihitung manual menggunakan Microsoft Excel — sebuah sumber kebenaran independen dari kode Python.

### Cara Menjalankan

```bash
# Tanpa pytest (built-in __main__, exit code mencerminkan hasil)
python -m tests.test_parity

# Dengan pytest
pip install -r requirements-dev.txt
pytest tests/test_parity.py -v
```

### Data Uji

`tests/fixtures/submissions.zip` berisi dua *project root* nyata (`ML-D_362258302025_Marimar/main.py` dan `ML-D_362258302026_Pulgoso/tugas.py`) — program CRUD sederhana dengan kemiripan struktural sebagian, hasil dari pengujian skenario nyata yang juga dihitung manual di Excel.

### Cakupan 39 Assertion (11 Kelompok)

| ID | Nama | Apa yang Dibuktikan |
|---|---|---|
| T1 | Preprocessing | Komentar dan *whitespace* benar-benar terhapus; *case folding* konsisten; panjang teks akhir sesuai nilai yang sudah diverifikasi manual |
| T2 | Char Map Accuracy | Setiap elemen `char_map` memetakan balik ke karakter asli yang **benar**, diuji untuk **seluruh** indeks (bukan sampel) |
| T3 | Rolling Hash | Nilai *rolling hash* untuk 50 *k-gram* pertama identik dengan hash naif — membuktikan korektnasi rumus *rolling update* |
| T4 | Fingerprint Counts | `\|FP1\|` dan `\|FP2\|` sesuai nilai Excel (194 dan 200) |
| T5 | Jaccard Components | Intersection (106), Union (288), dan Jaccard (36.8056%) sesuai Excel hingga toleransi 0.001% |
| T6 | Threshold Categorization | Hasil akhir masuk kategori Moderat sesuai aturan ambang batas |
| T7 | Threshold Boundaries | Keenam titik batas (`29.9%→Low`, `30.0%→Moderate`, `80.0%→Moderate`, `80.1%→High`, dst.) diuji satu per satu |
| T8 | Highlight Coverage | Baris yang disorot bukan nol, bukan semua baris (pembuktian highlight bekerja proporsional, bukan *all-or-nothing*) |
| T9 | ZIP Wrapper Detection | *Wrapper folder* (mis. `submissions/`) terdeteksi dan di-*strip* otomatis |
| T10 | Single Project Error | `ValueError` informatif saat hanya 1 *project* ditemukan |
| T11 | No Supported Files Error | `ValueError` informatif saat tidak ada `.py`/`.php`/`.dart` ditemukan |

### Integrasi Continuous Integration

Setiap `push` dan `pull request` ke *branch* `main` memicu `python -m tests.test_parity` secara otomatis lewat GitHub Actions (`.github/workflows/test.yml`). *Badge* status di README mencerminkan hasil terakhir.

## 2. Pengujian Black-Box (Alur UI)

Pengujian *black-box* memverifikasi perilaku sistem dari sudut pandang pengguna akhir, tanpa memeriksa implementasi internal. Skenario berikut dipakai dalam pengujian Tugas Akhir:

| # | Skenario | Kategori | Expected Output | Kriteria Lulus |
|---|---|---|---|---|
| A | Upload `.zip` valid (≥2 *project*, file `.php`/`.dart`/`.py`) | *Normal* | File diterima, tombol START ANALYSIS aktif | Tidak ada pesan *error*; tombol tidak `disabled` |
| B | Klik START ANALYSIS pada file valid | *Normal* | *Progress bar* berjalan, navigasi otomatis ke Comparisons | Halaman Comparisons tampil dengan ≥1 pasangan |
| C | Tampilan hasil *similarity* | *Normal* | Persentase dan tabel rincian *file* muncul dengan *badge* warna sesuai *threshold* | Nilai akurat, navigasi antar halaman berfungsi |
| D | `.zip` hanya berisi 1 *project root* | *Error* | Pesan *error*: "Hanya ditemukan 1 project... diperlukan minimal 2" | Pesan tampil jelas, sistem tidak *crash* |
| E | `.zip` tanpa file `.php`/`.dart`/`.py` | *Error* | Pesan *error*: "Tidak ada file ... yang ditemukan" | Pesan tampil jelas, sistem tidak *crash* |
| F | Upload file bukan `.zip` (mis. `.pdf`) | *Error* | Komponen *uploader* menolak sebelum dikirim ke *backend* (`type=["zip"]`) | File tidak dapat dipilih |
| G | `.zip` rusak/*corrupt* | *Error* | Pesan *error*: "File yang diunggah bukan arsip .zip yang valid" | Pesan tampil jelas, sistem tidak *crash* |
| H | Klik START ANALYSIS sebelum upload | *Edge* | Tombol dalam kondisi `disabled` | Tombol tidak responsif terhadap klik |
| I | Navigasi langsung ke *route* tengah (mis. Comparisons) tanpa Upload | *Edge* | `_guard_route()` mengarahkan kembali ke Upload dengan peringatan | Tidak ada halaman kosong/*crash* |
| J | `.zip` dengan *wrapper folder* (hasil "Compress to ZIP") | *Normal* | Sistem mendeteksi otomatis dan tetap berhasil mengekstrak | Analisis berjalan normal |

## 3. Evaluasi Akurasi (Uji Validitas Algoritma)

Karena sistem ini adalah instrumen deteksi langsung — bukan model *machine learning* dengan dataset berlabel — performa dinilai melalui **Uji Validitas Algoritma**: perbandingan langsung hasil komputasi sistem terhadap simulasi manual yang dijadikan acuan (*gold standard*).

**Prosedur:**

1. Simulasikan seluruh pipeline (Preprocessing → K-Gram → Hashing → Winnowing → Jaccard) secara manual menggunakan formula Microsoft Excel native, independen dari kode Python.
2. Bandingkan setiap komponen perantara (jumlah *fingerprint*, *intersection*, *union*) — bukan hanya hasil akhir — untuk memastikan kesetaraan di setiap tahap, bukan hanya kebetulan pada hasil akhir.
3. Verifikasi otomatis lewat `tests/test_parity.py` agar kesetaraan ini dapat direproduksi kapan saja tanpa pengecekan manual berulang.

Sistem dinyatakan valid karena seluruh komponen perantara dan hasil akhir identik dengan simulasi manual hingga presisi yang diuji (toleransi `0.001%` untuk akumulasi *floating point*).
